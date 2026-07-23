"""PMO 项目监控分析 — 统计指标计算"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
from config import BATCHES, SYSTEM_TYPES, BATCH_DEADLINES, NEAR_DUE_DAYS, REQUIRED_FIELDS
from data_loader import pct, is_filled


def task_row(row, report_date, days_diff, tag):
    """构造逾期/临期任务行"""
    return {
        'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
        'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
        'task': str(row.get('任务名称', ''))[:80], 'type': str(row.get('任务类型', '')),
        'priority': str(row.get('优先级', '')), 'status': str(row.get('状态_标准', '')),
        'person': str(row.get('负责人', '')), 'progress': str(row.get('进度', '')),
        'start': str(row.get('开始日期', '')), 'end': str(row.get('结束日期', '')),
        'days_diff': days_diff, 'tag': tag,
        'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因', '')) and str(row.get('延期原因', '')) not in ['-', 'nan'] else '（未填写）',
    }


# ============================================================
# 逾期 & 临期
# ============================================================
def compute_risk(df, report_date):
    """计算逾期和临期任务"""
    not_closed = ~df['状态_标准'].isin(['已完成', '已取消'])
    overdue_list = []
    near_due_list = []
    if '结束日期_dt' in df.columns:
        odf = df[not_closed & (df['结束日期_dt'] < report_date)]
        ndf = df[not_closed & (df['结束日期_dt'] >= report_date) & (df['结束日期_dt'] <= report_date + timedelta(days=NEAR_DUE_DAYS))]
        for _, row in odf.iterrows():
            days_overdue = (report_date - row['结束日期_dt']).days
            overdue_list.append(task_row(row, report_date, days_overdue, '逾期'))
        for _, row in ndf.iterrows():
            days_left = (row['结束日期_dt'] - report_date).days
            near_due_list.append(task_row(row, report_date, days_left, '临期'))
    return overdue_list, near_due_list


# ============================================================
# 项目完成率排名
# ============================================================
def compute_proj_ranking(df, overdue_list, near_due_list):
    """计算各项目标段完成率排名"""
    proj_ranking = []
    for proj in sorted(df['项目'].unique()):
        pdf = df[df['项目'] == proj]
        pdone = len(pdf[pdf['完成标记'] == '已完成'])
        batch = pdf['批次'].iloc[0]
        syst = pdf['系统类型'].iloc[0]
        proj_ranking.append({
            'project': proj, 'batch': batch, 'system': syst,
            'total': len(pdf), 'done': pdone,
            'undone': len(pdf) - pdone, 'rate': pct(pdone, len(pdf)),
            'days': int(pdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['project'] == proj]),
            'near_due': len([x for x in near_due_list if x['project'] == proj]),
        })
    proj_ranking.sort(key=lambda x: x['rate'])
    return proj_ranking


# ============================================================
# KPI
# ============================================================
def compute_kpi(df, overdue_list, near_due_list):
    """计算核心KPI指标"""
    done_df = df[df['完成标记'] == '已完成']
    undone_df = df[df['完成标记'] == '未完成']
    return {
        'total': len(df), 'done': len(done_df), 'undone': len(undone_df),
        'comp_rate': pct(len(done_df), len(df)),
        'total_days': int(df['人天数值'].sum()),
        'overdue': len(overdue_list), 'near_due': len(near_due_list),
        'projects': int(df['项目'].nunique()), 'modules': int(df['模块'].nunique()),
        'people': int(df['负责人'].nunique()),
    }


# ============================================================
# 批次KPI
# ============================================================
def compute_batch_kpi(df, overdue_list, near_due_list):
    """按批次统计KPI"""
    batch_kpi = []
    for batch in BATCHES:
        bdf = df[df['批次'] == batch]
        bdone = len(bdf[bdf['完成标记'] == '已完成'])
        batch_kpi.append({
            'batch': batch, 'total': len(bdf), 'done': bdone, 'undone': len(bdf) - bdone,
            'comp_rate': pct(bdone, len(bdf)), 'days': int(bdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['batch'] == batch]),
            'near_due': len([x for x in near_due_list if x['batch'] == batch]),
            'projects': int(bdf['项目'].nunique()),
        })
    return batch_kpi


# ============================================================
# 系统类型KPI
# ============================================================
def compute_system_kpi(df, overdue_list, near_due_list):
    """按系统类型统计KPI"""
    system_kpi = []
    for st in SYSTEM_TYPES:
        sdf = df[df['系统类型'] == st]
        sd = len(sdf[sdf['完成标记'] == '已完成'])
        system_kpi.append({
            'system': st, 'total': len(sdf), 'done': sd, 'undone': len(sdf) - sd,
            'comp_rate': pct(sd, len(sdf)), 'days': int(sdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['system'] == st]),
            'near_due': len([x for x in near_due_list if x['system'] == st]),
            'projects': int(sdf['项目'].nunique()),
        })
    return system_kpi


# ============================================================
# 批次 × 系统类型
# ============================================================
def compute_batch_system(df):
    """批次 × 系统类型交叉统计"""
    batch_system = []
    for batch in BATCHES:
        for st in SYSTEM_TYPES:
            bs = df[(df['批次'] == batch) & (df['系统类型'] == st)]
            if len(bs) == 0:
                continue
            bsd = len(bs[bs['完成标记'] == '已完成'])
            batch_system.append({
                'batch': batch, 'system': st, 'total': len(bs),
                'done': bsd, 'undone': len(bs) - bsd, 'comp_rate': pct(bsd, len(bs)),
                'days': int(bs['人天数值'].sum()),
            })
    return batch_system


# ============================================================
# 供应商 × 批次 × 系统类型
# ============================================================
def compute_team_detail(df):
    """供应商团队绩效统计"""
    team_detail = []
    for team in sorted(df['供应商团队'].unique()):
        for batch in BATCHES:
            for st in SYSTEM_TYPES:
                tb = df[(df['供应商团队'] == team) & (df['批次'] == batch) & (df['系统类型'] == st)]
                if len(tb) == 0:
                    continue
                tbd = len(tb[tb['完成标记'] == '已完成'])
                team_detail.append({
                    'team': team, 'batch': batch, 'system': st,
                    'total': len(tb), 'done': tbd, 'undone': len(tb) - tbd,
                    'comp_rate': pct(tbd, len(tb)), 'days': int(tb['人天数值'].sum()),
                })
    return team_detail


# ============================================================
# 模块 × 批次 × 系统类型
# ============================================================
def compute_module_detail(df):
    """模块完成率明细统计"""
    module_detail = []
    for mod in sorted(df['模块'].unique()):
        for batch in BATCHES:
            for st in SYSTEM_TYPES:
                mb = df[(df['模块'] == mod) & (df['批次'] == batch) & (df['系统类型'] == st)]
                if len(mb) == 0:
                    continue
                mbd = len(mb[mb['完成标记'] == '已完成'])
                module_detail.append({
                    'module': mod, 'batch': batch, 'system': st,
                    'total': len(mb), 'done': mbd, 'undone': len(mb) - mbd,
                    'comp_rate': pct(mbd, len(mb)), 'days': int(mb['人天数值'].sum()),
                })
    return module_detail


# ============================================================
# 未完成任务明细
# ============================================================
def compute_undone_detail(df):
    """未完成任务明细表"""
    undone_df = df[df['完成标记'] == '未完成']
    undone_detail = []
    for _, row in undone_df.iterrows():
        undone_detail.append({
            'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
            'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
            'task': str(row.get('任务名称', ''))[:60], 'type': str(row.get('任务类型', '')),
            'priority': str(row.get('优先级', '')), 'status': str(row.get('状态_标准', '')),
            'person': str(row.get('负责人', '')), 'progress': str(row.get('进度', '')),
            'days': row['人天数值'],
        })
    return undone_detail


# ============================================================
# 阶段漏斗
# ============================================================
def compute_stage_funnel(df):
    """FS → 业务测试 → TS 阶段漏斗分析"""
    done_df = df[df['完成标记'] == '已完成']
    undone_df = df[df['完成标记'] == '未完成']
    stage_cols = [
        ('FS-功能说明书', 'FS状态_标准'),
        ('业务测试', '业务测试状态_标准'),
        ('TS-技术说明书', 'TS状态_标准'),
    ]
    stage_funnel = []
    for name, col in stage_cols:
        if col not in df.columns:
            continue
        valid = df[~df[col].isin(['-', '不适用', ''])]
        done_valid = done_df[~done_df[col].isin(['-', '不适用', ''])]
        undone_valid = undone_df[~undone_df[col].isin(['-', '不适用', ''])]
        stage_funnel.append({
            'stage': name,
            'all_total': len(valid), 'all_done': int(len(valid[valid == '已完成'])),
            'all_rate': pct(len(valid[valid == '已完成']), len(valid)),
            'done_total': len(done_valid), 'done_finished': int(len(done_valid[done_valid == '已完成'])),
            'done_rate': pct(len(done_valid[done_valid == '已完成']), len(done_valid)),
            'undone_total': len(undone_valid), 'undone_finished': int(len(undone_valid[undone_valid == '已完成'])),
            'undone_rate': pct(len(undone_valid[undone_valid == '已完成']), len(undone_valid)),
            'undone_pending': int(len(undone_valid[undone_valid.isin(['待处理', '进行中'])])),
        })
    return stage_funnel


# ============================================================
# 必填字段完整度
# ============================================================
def compute_field_completeness(df):
    """必填字段完整度分析"""
    total = len(df)
    undone_df = df[df['完成标记'] == '未完成']

    # 每行必填字段计数
    df['_filled_count'] = df.apply(lambda row: sum(1 for f in REQUIRED_FIELDS if f in df.columns and is_filled(row[f])), axis=1)
    df['_completeness'] = df['_filled_count'] / len(REQUIRED_FIELDS) * 100

    # 各字段填写率
    field_comp_all = []
    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            continue
        filled = df[field].apply(is_filled).sum()
        field_comp_all.append({'field': field, 'filled': int(filled), 'missing': total - int(filled), 'rate': pct(filled, total)})

    # 批次×系统类型字段完整度
    batch_system_field_comp = []
    for batch in BATCHES:
        for st in SYSTEM_TYPES:
            bf = df[(df['批次'] == batch) & (df['系统类型'] == st)]
            if len(bf) == 0:
                continue
            batch_system_field_comp.append({
                'batch': batch, 'system': st, 'total': len(bf),
                'avg_rate': round(bf['_completeness'].mean(), 1),
                'perfect': int(len(bf[bf['_completeness'] == 100])),
                'perfect_rate': pct(len(bf[bf['_completeness'] == 100]), len(bf)),
            })

    # 未完成任务必填字段问题
    undone_field_issues = []
    for _, row in undone_df.iterrows():
        missing = [f for f in REQUIRED_FIELDS if f in df.columns and not is_filled(row[f])]
        if missing:
            undone_field_issues.append({
                'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
                'system': str(row.get('系统类型', '')),
                'task': str(row.get('任务名称', ''))[:60], 'status': str(row.get('状态_标准', '')),
                'person': str(row.get('负责人', '')),
                'missing_count': len(missing), 'missing_fields': ', '.join(missing),
            })
    undone_field_issues.sort(key=lambda x: x['missing_count'], reverse=True)

    return field_comp_all, batch_system_field_comp, undone_field_issues[:50]


# ============================================================
# 月度趋势
# ============================================================
def compute_monthly_trend(df):
    """月度完成趋势"""
    if '结束日期_dt' not in df.columns or df['结束日期_dt'].notna().sum() == 0:
        return []
    monthly = df.groupby(df['结束日期_dt'].dt.to_period('M').astype(str)).agg(
        完成任务=('完成标记', lambda x: (x == '已完成').sum()),
        总任务=('状态_标准', 'count'),
    ).reset_index()
    monthly.columns = ['month', 'done', 'total']
    monthly['rate'] = (monthly['done'] / monthly['total'] * 100).round(1)
    return monthly.to_dict('records')


# ============================================================
# 批次上线时间节点
# ============================================================
def compute_deadline_analysis(df, report_date):
    """批次上线时间节点 & 开发截止预警"""
    deadline_analysis = []
    for batch, dls in BATCH_DEADLINES.items():
        dev_dl = pd.Timestamp(dls['开发截止'])
        go_live = pd.Timestamp(dls['上线'])
        bdf = df[(df['批次'] == batch) & df['结束日期_dt'].notna()]
        if len(bdf) == 0:
            continue
        not_closed_b = ~bdf['状态_标准'].isin(['已完成', '已取消'])
        over_dev = bdf[not_closed_b & (bdf['结束日期_dt'] > dev_dl)]
        done_late = bdf[(bdf['状态_标准'] == '已完成') & (bdf['结束日期_dt'] > dev_dl)]
        days_to_dl = (dev_dl - report_date).days
        deadline_analysis.append({
            'batch': batch,
            'go_live': go_live.strftime('%Y/%m/%d'),
            'dev_deadline': dev_dl.strftime('%Y/%m/%d'),
            'days_left': days_to_dl,
            'total': len(bdf),
            'done': int(len(bdf[bdf['状态_标准'] == '已完成'])),
            'done_rate': pct(len(bdf[bdf['状态_标准'] == '已完成']), len(bdf)),
            'over_dev': len(over_dev),
            'done_late': len(done_late),
            'urgent': 0 <= days_to_dl <= 7,
            'past_due': days_to_dl < 0,
        })
    return deadline_analysis


# ============================================================
# 已完成任务验收就绪分析
# ============================================================
def compute_acceptance(df):
    """已完成任务的验收就绪分析（测试报告 & 业务测试）"""
    done_df = df[df['完成标记'] == '已完成']
    acceptance = []
    for _, row in done_df.iterrows():
        # 测试报告检查
        tests = []
        for tc in ['系统测试报告', '集成测试报告', '回归测试报告']:
            if tc in df.columns:
                v = str(row.get(tc, ''))
                tests.append(v not in ['', '-', 'nan', 'None'])
        bt_status = str(row.get('业务测试状态_标准', ''))
        bt_start = str(row.get('业务测试实际开始日期', ''))
        bt_end = str(row.get('业务测试实际结束日期', ''))
        bt_ok = bt_status in ['已完成'] and bt_start not in ['', '-', 'nan', 'None'] and bt_end not in ['', '-', 'nan', 'None']
        test_count = sum(tests)
        acceptance.append({
            'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
            'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
            'task': str(row.get('任务名称', ''))[:60],
            'type': str(row.get('任务类型', '')), 'person': str(row.get('负责人', '')),
            'end_date': str(row.get('结束日期', '')),
            'bt_status': bt_status,
            'bt_start': bt_start if bt_start not in ['-', 'nan', ''] else '（未填）',
            'bt_end': bt_end if bt_end not in ['-', 'nan', ''] else '（未填）',
            'sys_test': '✅' if (len(tests) > 0 and tests[0]) else '❌',
            'integ_test': '✅' if (len(tests) > 1 and tests[1]) else '❌',
            'regr_test': '✅' if (len(tests) > 2 and tests[2]) else '❌',
            'test_count': test_count,
            'all_ready': test_count == 3 and bt_ok,
        })

    # 验收汇总（按项目×批次×系统）
    acc_summary = []
    for proj in sorted(df['项目'].unique()):
        pacc = [a for a in acceptance if a['project'] == proj]
        if not pacc:
            continue
        batch = pacc[0]['batch']
        syst = pacc[0]['system']
        acc_summary.append({
            'project': proj, 'batch': batch, 'system': syst,
            'total_done': len(pacc),
            'bt_complete': sum(1 for a in pacc if a['bt_status'] == '已完成'),
            'sys_test_ok': sum(1 for a in pacc if a['sys_test'] == '✅'),
            'integ_test_ok': sum(1 for a in pacc if a['integ_test'] == '✅'),
            'regr_test_ok': sum(1 for a in pacc if a['regr_test'] == '✅'),
            'all_ready': sum(1 for a in pacc if a['all_ready']),
            'ready_rate': pct(sum(1 for a in pacc if a['all_ready']), len(pacc)),
        })

    return acceptance, acc_summary


# ============================================================
# 延期任务详情（含延期原因和备注）
# ============================================================
def enrich_risk_with_reason(df, overdue_list, near_due_list):
    """为期满/临期任务补充延期原因和备注"""
    delayed_detail = []
    for item in overdue_list:
        orig = df[(df['项目'] == item['project']) & (df['任务名称'].str[:30] == item['task'][:30])]
        if len(orig) > 0:
            row = orig.iloc[0]
            item['reason'] = str(row.get('延期原因', '')) if pd.notna(row.get('延期原因', '')) and str(row.get('延期原因', '')) not in ['-', 'nan'] else '（未填写）'
            item['remark'] = str(row.get('备注', '')) if pd.notna(row.get('备注', '')) and str(row.get('备注', '')) not in ['-', 'nan'] else '（无备注）'
        else:
            item['reason'] = '（未填写）'
            item['remark'] = '（无备注）'
        delayed_detail.append(item)
    for item in near_due_list:
        orig = df[(df['项目'] == item['project']) & (df['任务名称'].str[:30] == item['task'][:30])]
        if len(orig) > 0:
            row = orig.iloc[0]
            item['reason'] = str(row.get('延期原因', '')) if pd.notna(row.get('延期原因', '')) and str(row.get('延期原因', '')) not in ['-', 'nan'] else '（未填写）'
            item['remark'] = str(row.get('备注', '')) if pd.notna(row.get('备注', '')) and str(row.get('备注', '')) not in ['-', 'nan'] else '（无备注）'
        else:
            item['reason'] = '（未填写）'
            item['remark'] = '（无备注）'
    return delayed_detail


# ============================================================
# 总入口：计算所有统计指标
# ============================================================
def compute_all_stats(df, report_date_str='2026/7/22'):
    """计算所有分析统计指标（含数据质量维度），返回字典"""
    report_date = pd.Timestamp(report_date_str)

    # 逾期 & 临期
    overdue_list, near_due_list = compute_risk(df, report_date)

    # 数据质量（作为原生统计维度，与其他维度并列）
    from data_quality import compute_quality_dimension
    quality = compute_quality_dimension(df)

    # 各模块统计
    proj_ranking = compute_proj_ranking(df, overdue_list, near_due_list)
    kpi = compute_kpi(df, overdue_list, near_due_list)
    batch_kpi = compute_batch_kpi(df, overdue_list, near_due_list)
    system_kpi = compute_system_kpi(df, overdue_list, near_due_list)
    batch_system = compute_batch_system(df)
    team_detail = compute_team_detail(df)
    module_detail = compute_module_detail(df)
    undone_detail = compute_undone_detail(df)
    stage_funnel = compute_stage_funnel(df)
    field_comp_all, batch_system_field_comp, undone_field_issues = compute_field_completeness(df)
    monthly_detail = compute_monthly_trend(df)
    deadline_analysis = compute_deadline_analysis(df, report_date)
    acceptance, acc_summary = compute_acceptance(df)
    delayed_detail = enrich_risk_with_reason(df, overdue_list, near_due_list)

    return {
        'report_date': report_date_str, 'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'kpi': kpi, 'overdue_list': delayed_detail, 'near_due_list': near_due_list,
        'proj_ranking': proj_ranking,
        'batch_kpi': batch_kpi, 'system_kpi': system_kpi, 'batch_system': batch_system,
        'team_detail': team_detail, 'module_detail': module_detail,
        'undone_detail': undone_detail, 'stage_funnel': stage_funnel,
        'field_comp_all': field_comp_all, 'batch_system_field_comp': batch_system_field_comp,
        'undone_field_issues': undone_field_issues,
        'monthly_detail': monthly_detail,
        'deadline_analysis': deadline_analysis,
        'acceptance': acceptance, 'acc_summary': acc_summary,
        'quality': quality,  # 数据质量作为原生统计维度
        'batches': BATCHES, 'REQUIRED_FIELDS': REQUIRED_FIELDS, 'required_count': len(REQUIRED_FIELDS),
    }
