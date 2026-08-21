# -*- coding: utf-8 -*-
"""PMO 项目监控分析 — 历史快照多日对比引擎

职责：
1. 扫描 data/ 目录下历史快照（文件名日期解析），确定对比窗口（当前 + 最近 N-1 个历史快照）
2. 清洗后 DataFrame 的 pkl 缓存，避免每次重复解析 Excel
3. 生成每个项目的多日指标序列（series：数量变化 + 完成率变化）
4. 生成相邻快照之间的任务级变化明细（pair diffs：新完成/进度提升/新启动/状态回退/新增/消失）
"""

import os, re, glob, pickle
import pandas as pd
from data_loader import load_and_clean, pct

MAX_SNAPSHOTS = 6      # 对比窗口：当前 + 最近 5 个历史快照
CACHE_DIR_NAME = '.history_cache'


def parse_date_from_name(fname):
    """从文件名解析快照日期（_YYYY_M_D.xlsx），失败返回 None"""
    m = re.search(r'_(\d{4})_(\d{1,2})_(\d{1,2})\.xlsx$', fname)
    if not m:
        return None
    return pd.Timestamp(f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}')


def find_snapshots(data_dir):
    """返回 [(date, path)] 按日期升序；跳过临时文件/模板/报告等非快照文件"""
    out = []
    for f in glob.glob(os.path.join(data_dir, '*.xlsx')):
        b = os.path.basename(f)
        if b.startswith('~$') or '模板' in b or 'PMO监控分析报告' in b:
            continue
        d = parse_date_from_name(b)
        if d is None:
            continue
        out.append((d, f))
    out.sort(key=lambda x: x[0])
    return out


def load_cached(snapshot_path, cache_dir):
    """带 pkl 缓存的快照加载：缓存键 = 文件修改时间，防止旧缓存误用"""
    mtime = os.path.getmtime(snapshot_path)
    os.makedirs(cache_dir, exist_ok=True)
    key = os.path.basename(snapshot_path).replace('.xlsx', '')
    cache_path = os.path.join(cache_dir, f'{key}.pkl')
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as fh:
                cached = pickle.load(fh)
            if cached.get('mtime') == mtime:
                return cached['df']
        except Exception:
            pass
    df = load_and_clean(snapshot_path)
    try:
        with open(cache_path, 'wb') as fh:
            pickle.dump({'mtime': mtime, 'df': df}, fh)
    except Exception:
        pass  # 缓存写入失败不影响主流程
    return df


def _fmt_prog(v):
    """0~1 的进度数值 → '30%'"""
    return f'{v * 100:.0f}%'


def _agg_stats(g):
    """对一个项目的子集 DataFrame 计算核心统计（口径与 stats_computer 一致：分母排除已取消）"""
    total = len(g)
    done = int((g['完成标记'] == '已完成').sum())
    canc = int((g['完成标记'] == '已取消').sum())
    eff = total - canc
    mh = g[g['优先级'].isin(['高', '中'])]
    low = g[g['优先级'].isin(['低'])]
    mh_done = int((mh['完成标记'] == '已完成').sum())
    mh_canc = int((mh['完成标记'] == '已取消').sum())
    mh_ip = int((mh['状态_标准'] == '进行中').sum())
    low_done = int((low['完成标记'] == '已完成').sum())
    low_canc = int((low['完成标记'] == '已取消').sum())
    low_ip = int((low['状态_标准'] == '进行中').sum())
    bt_base = g[g['完成标记'] != '已取消']
    bt_done = int((bt_base['业务测试状态_标准'] == '已完成').sum()) if '业务测试状态_标准' in g.columns else 0
    return {
        'total': total, 'done': done, 'cancelled': canc,
        'rate': pct(done, eff),
        'mh_total': len(mh), 'mh_done': mh_done, 'mh_cancelled': mh_canc,
        'mh_in_progress': mh_ip, 'mh_remaining': len(mh) - mh_done - mh_canc,
        'mh_rate': pct(mh_done, len(mh) - mh_canc),
        'l_total': len(low), 'l_done': low_done, 'l_cancelled': low_canc,
        'l_in_progress': low_ip, 'l_remaining': len(low) - low_done - low_canc,
        'l_rate': pct(low_done, len(low) - low_canc),
        'bt_done': bt_done, 'bt_remaining': len(bt_base) - bt_done, 'bt_total': len(bt_base),
        'bt_rate': pct(bt_done, len(bt_base)) if len(bt_base) > 0 else 0,
    }


def _series_row(df, proj, date):
    """某个快照中某个项目的多日序列行（数量 + 完成率），项目不存在时返回 None"""
    p = df[df['项目'] == proj]
    if len(p) == 0:
        return None
    a = _agg_stats(p)
    return {
        'date': date.strftime('%Y/%m/%d'),
        'total': a['total'], 'done': a['done'],
        'undone': a['total'] - a['done'] - a['cancelled'],
        'in_progress': int((p['状态_标准'] == '进行中').sum()),
        'pending': int((p['状态_标准'] == '待处理').sum()),
        'cancelled': a['cancelled'],
        'rate': a['rate'], 'mh_rate': a['mh_rate'], 'bt_rate': a['bt_rate'],
        'mh_done': a['mh_done'], 'mh_remaining': a['mh_remaining'],
        'l_done': a['l_done'], 'l_remaining': a['l_remaining'], 'l_rate': a['l_rate'],
        'bt_done': a['bt_done'], 'bt_remaining': a['bt_remaining'],
    }


def _diff_pair(prev_df, curr_df):
    """相邻两个快照的任务级对齐，输出每个项目的变化明细与统计"""
    pdiffs = {}
    all_projects = set(curr_df['项目'].unique()) | set(prev_df['项目'].unique())
    for proj in all_projects:
        pp = prev_df[prev_df['项目'] == proj]
        cp = curr_df[curr_df['项目'] == proj]
        pmap = {r['任务名称']: r for _, r in pp.iterrows()}
        cmap = {r['任务名称']: r for _, r in cp.iterrows()}
        added = [t for t in cmap if t not in pmap]
        removed = [t for t in pmap if t not in cmap]

        new_done, started, progress_up, regressed = [], [], [], []
        bt_done_new, bt_started, bt_regressed = [], [], []
        for t, cr in cmap.items():
            if t not in pmap:
                continue
            pr = pmap[t]
            pst, cst = pr['状态_标准'], cr['状态_标准']
            pprog, cprog = pr['进度数值'], cr['进度数值']
            pmark, cmark = pr['完成标记'], cr['完成标记']
            base = {
                'task': t[:60], 'person': str(cr.get('负责人', '')),
                'before': f'{pst} {_fmt_prog(pprog)}', 'after': f'{cst} {_fmt_prog(cprog)}',
            }
            if pmark != '已完成' and cmark == '已完成':
                new_done.append(base)
            if pst == '待处理' and cst == '进行中':
                started.append(base)
            if pmark != '已完成' and cmark != '已完成' and cprog > pprog + 1e-6:
                progress_up.append(base)
            # 回退：已完成→未完成/已取消；进行中→待处理
            if (pmark == '已完成' and cmark != '已完成') or (pst == '进行中' and cst == '待处理'):
                regressed.append(base)
            # ===== 业务测试状态变化（较上期测试推进/回退） =====
            pbt = pr.get('业务测试状态_标准', '')
            cbt = cr.get('业务测试状态_标准', '')
            pbt_s = '-' if pd.isna(pbt) or str(pbt).strip() in ('', '-', 'nan') else str(pbt)
            cbt_s = '-' if pd.isna(cbt) or str(cbt).strip() in ('', '-', 'nan') else str(cbt)
            bt_person = cr.get('业务测试负责人', '')
            tbase = {
                'task': t[:60], 'person': str(bt_person) if pd.notna(bt_person) else '',
                'bt_before': pbt_s, 'bt_after': cbt_s,
            }
            if pbt_s != '已完成' and cbt_s == '已完成':
                bt_done_new.append(tbase)
            if pbt_s in ('-', '待处理') and cbt_s == '进行中':
                bt_started.append(tbase)
            if pbt_s == '已完成' and cbt_s != '已完成':
                bt_regressed.append(tbase)

        pdiffs[proj] = {
            'has_prev': len(pp) > 0,
            'prev': _agg_stats(pp), 'curr': _agg_stats(cp),
            'new_done': len(new_done), 'started': len(started),
            'progress_up': len(progress_up), 'regressed': len(regressed),
            'added': len(added), 'removed': len(removed),
            'bt_new_done': len(bt_done_new), 'bt_started': len(bt_started),
            'bt_regressed': len(bt_regressed),
            'new_done_list': new_done, 'started_list': started,
            'progress_up_list': progress_up, 'regressed_list': regressed,
            'bt_done_new_list': bt_done_new, 'bt_started_list': bt_started,
            'bt_regressed_list': bt_regressed,
            'added_list': [{'task': t[:60], 'person': str(cmap[t].get('负责人', ''))} for t in added],
            'removed_list': [{'task': t[:60], 'person': str(pmap[t].get('负责人', ''))} for t in removed],
        }
    return pdiffs


def build_trend(curr_df, data_dir, current_date=None, max_snapshots=MAX_SNAPSHOTS):
    """主入口：构建多日对比数据。

    curr_df: 当前快照的清洗后 DataFrame（data_loader.load_and_clean 产物）
    data_dir: 历史快照目录
    current_date: 当前快照日期（pd.Timestamp），默认取 data/ 中最新快照日期

    返回 None（无历史快照可用）或 {
        'dates': [日期字符串...],            # 对比窗口内快照（升序，含当前）
        'base_date': 上一快照日期字符串,     # Δ 对比基准
        'base_interval': 与基准间隔天数,
        'series': {项目: [行...]},           # 多日序列（行结构与 _series_row 一致，缺失日期为 None）
        'pairs': [{prev_date, curr_date, diff: {项目: 变化明细}}...],
        'proj_diff': {项目: 变化明细},        # 最新一期（上一快照 → 当前）对比，供表格 Δ 列
    }
    """
    snaps = find_snapshots(data_dir)
    if not snaps:
        return None
    if current_date is None:
        current_date = max(s[0] for s in snaps)
    eligible = [s for s in snaps if s[0] < current_date]
    prev_snaps = eligible[-(max_snapshots - 1):] if len(eligible) > (max_snapshots - 1) else eligible
    window = prev_snaps + [(current_date, None)]
    cache_dir = os.path.join(data_dir, CACHE_DIR_NAME)

    dfs = {}
    for d, path in window:
        dfs[d] = curr_df if path is None else load_cached(path, cache_dir)
    dates = sorted(dfs.keys())

    # 项目多日序列
    series = {}
    for proj in curr_df['项目'].unique():
        series[proj] = [_series_row(dfs[d], proj, d) for d in dates]

    # 相邻快照变化明细
    pairs = []
    for i in range(1, len(dates)):
        pairs.append({
            'prev_date': dates[i - 1].strftime('%Y/%m/%d'),
            'curr_date': dates[i].strftime('%Y/%m/%d'),
            'diff': _diff_pair(dfs[dates[i - 1]], dfs[dates[i]]),
        })

    base = dates[-2] if len(dates) >= 2 else None
    return {
        'dates': [d.strftime('%Y/%m/%d') for d in dates],
        'base_date': base.strftime('%Y/%m/%d') if base is not None else None,
        'base_interval': (dates[-1] - base).days if base is not None else None,
        'series': series,
        'pairs': pairs,
        'proj_diff': pairs[-1]['diff'] if pairs else {},
    }
