#!/usr/bin/env python3
"""
PMO 项目监控分析工具 — 国电投1455项目
支持输出 HTML 报告。

用法:
  python pmo_analyzer.py <输入.xlsx>                     # 生成 HTML 报告
  python pmo_analyzer.py <输入.xlsx> -o report.html -d 2026/7/22
"""

import pandas as pd
import numpy as np
import json
import sys, os, argparse, warnings
from datetime import datetime, timedelta
from collections import Counter
warnings.filterwarnings('ignore')

REQUIRED_FIELDS = [
    '任务名称','任务类型','选择类型','优先级','状态','负责人','进度',
    '开始日期','结束日期','描述','FS状态','FS负责人','FS计划结束日期',
    '业务测试状态','业务测试负责人','业务测试计划开始日期','业务测试计划结束日期','TS状态'
]

BATCHES = ['A批次','B批次','C批次','未标注批次']
JAVA_PROJECT_KW = ['智能仓储','合同管理','BPM','报销报账','共享融合','司库融合','MDG-JAVA','BPC前端','电子档案']
JAVA_MODULE_KW = ['智能仓储','合同管理','BPM','报销报账','财务共享系统改造','司库融合','MDG','电子档案','SSF']
NEAR_DUE_DAYS = 7  # 临期天数


def pct(a, b):
    return round(a/b*100, 1) if b > 0 else 0


def is_filled(val):
    if pd.isna(val): return False
    s = str(val).strip()
    return s != '' and s != '-' and s != 'nan'


def extract_batch(proj):
    if pd.isna(proj): return '未标注批次'
    p = str(proj)
    if '-A批次' in p or p.endswith('-A'): return 'A批次'
    if '-B批次' in p or p.endswith('-B'): return 'B批次'
    if '-C批次' in p or '-C' in p or 'Ｃ批次' in p: return 'C批次'
    return '未标注批次'


def extract_team(proj):
    if pd.isna(proj): return '未知'
    p = str(proj)
    for kw in ['石化盈科','昆仑数智','上海汉得','青岛海信','山能数科','中核核信','浪潮','中远海科']:
        if kw in p: return kw
    return '内部/其他'


def classify_system(row):
    proj = str(row.get('项目',''))
    mod = str(row.get('模块',''))
    for kw in JAVA_PROJECT_KW:
        if kw in proj: return 'JAVA-专业系统'
    for kw in JAVA_MODULE_KW:
        if kw in mod: return 'JAVA-专业系统'
    return 'SAP'


def load_and_clean(filepath):
    df = pd.read_excel(filepath, sheet_name=0)
    col_map = {'清单项名称': '任务名称'}
    df.rename(columns=col_map, inplace=True)

    status_map = {'已经完成': '已完成', '未开始': '待处理', '已阻塞': '进行中'}
    df['状态_标准'] = df['状态'].replace(status_map)
    if 'FS状态' in df.columns:
        df['FS状态_标准'] = df['FS状态'].replace({'完成': '已完成'}).replace(status_map)
    if '业务测试状态' in df.columns:
        df['业务测试状态_标准'] = df['业务测试状态'].replace({'已经完成': '已完成', '测试中': '进行中', '': '-'})
    if 'TS状态' in df.columns:
        df['TS状态_标准'] = df['TS状态'].replace(status_map)

    df['进度数值'] = df['进度'].astype(str).str.replace('%','').apply(
        lambda x: float(x) if x.replace('.','').isdigit() else 0) / 100
    df['人天数值'] = pd.to_numeric(df['计划开发人天'], errors='coerce').fillna(0)

    for dcol in ['开始日期','结束日期']:
        if dcol in df.columns:
            df[dcol + '_dt'] = pd.to_datetime(df[dcol], format='%Y/%m/%d', errors='coerce')
    if '开始日期_dt' in df.columns and '结束日期_dt' in df.columns:
        df['任务周期'] = (df['结束日期_dt'] - df['开始日期_dt']).dt.days

    if '项目' in df.columns:
        df['批次'] = df['项目'].apply(extract_batch)
        df['供应商团队'] = df['项目'].apply(extract_team)
    df['系统类型'] = df.apply(classify_system, axis=1)
    df['完成标记'] = df['状态_标准'].apply(lambda x: '已完成' if x == '已完成' else '未完成')
    return df


# ============================================================
# 工具函数：统一维度聚合
# ============================================================
def dim_label(row, dims):
    """从行数据提取维度标签"""
    parts = []
    if '项目' in dims: parts.append(str(row.get('项目','')))
    if '批次' in dims: parts.append(str(row.get('批次','')))
    if '系统类型' in dims: parts.append(str(row.get('系统类型','')))
    return ' | '.join(parts)


def make_table(rows, headers, key='rows'):
    """rows: list of dict, headers: list of (key, label)"""
    return {'headers': [h[1] for h in headers], 'keys': [h[0] for h in headers], 'rows': rows}


# ============================================================
# 核心统计
# ============================================================
def compute_all_stats(df, report_date_str='2026/7/22'):
    report_date = pd.Timestamp(report_date_str)
    total = len(df)
    done_df = df[df['完成标记']=='已完成']
    undone_df = df[df['完成标记']=='未完成']
    not_closed = ~df['状态_标准'].isin(['已完成','已取消'])

    # === 逾期 & 临期（基于日期判断）===
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


    # === 项目完成率排名 ===
    proj_ranking = []
    for proj in sorted(df['项目'].unique()):
        pdf = df[df['项目']==proj]
        pdone = len(pdf[pdf['完成标记']=='已完成'])
        batch = pdf['批次'].iloc[0]
        syst = pdf['系统类型'].iloc[0]
        proj_ranking.append({
            'project': proj, 'batch': batch, 'system': syst,
            'total': len(pdf), 'done': pdone,
            'undone': len(pdf)-pdone, 'rate': pct(pdone, len(pdf)),
            'days': int(pdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['project']==proj]),
            'near_due': len([x for x in near_due_list if x['project']==proj]),
        })
    proj_ranking.sort(key=lambda x: x['rate'])

    # === KPI ===
    kpi = {
        'total': total, 'done': len(done_df), 'undone': len(undone_df),
        'comp_rate': pct(len(done_df), total),
        'total_days': int(df['人天数值'].sum()),
        'overdue': len(overdue_list), 'near_due': len(near_due_list),
        'projects': int(df['项目'].nunique()), 'modules': int(df['模块'].nunique()),
        'people': int(df['负责人'].nunique()),
    }

    # === 批次KPI ===
    batch_kpi = []
    for batch in BATCHES:
        bdf = df[df['批次']==batch]
        bdone = len(bdf[bdf['完成标记']=='已完成'])
        batch_kpi.append({
            'batch': batch, 'total': len(bdf), 'done': bdone, 'undone': len(bdf)-bdone,
            'comp_rate': pct(bdone, len(bdf)), 'days': int(bdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['batch']==batch]),
            'near_due': len([x for x in near_due_list if x['batch']==batch]),
            'projects': int(bdf['项目'].nunique()),
        })

    # === 系统类型KPI ===
    system_kpi = []
    for st in ['JAVA-专业系统','SAP']:
        sdf = df[df['系统类型']==st]
        sd = len(sdf[sdf['完成标记']=='已完成'])
        system_kpi.append({
            'system': st, 'total': len(sdf), 'done': sd, 'undone': len(sdf)-sd,
            'comp_rate': pct(sd, len(sdf)), 'days': int(sdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['system']==st]),
            'near_due': len([x for x in near_due_list if x['system']==st]),
            'projects': int(sdf['项目'].nunique()),
        })

    # === 批次×系统类型 ===
    batch_system = []
    for batch in BATCHES:
        for st in ['JAVA-专业系统','SAP']:
            bs = df[(df['批次']==batch)&(df['系统类型']==st)]
            if len(bs)==0: continue
            bsd = len(bs[bs['完成标记']=='已完成'])
            batch_system.append({
                'batch': batch, 'system': st, 'total': len(bs),
                'done': bsd, 'undone': len(bs)-bsd, 'comp_rate': pct(bsd, len(bs)),
                'days': int(bs['人天数值'].sum()),
            })

    # === 供应商×批次×系统类型 ===
    team_detail = []
    for team in sorted(df['供应商团队'].unique()):
        for batch in BATCHES:
            for st in ['JAVA-专业系统','SAP']:
                tb = df[(df['供应商团队']==team)&(df['批次']==batch)&(df['系统类型']==st)]
                if len(tb)==0: continue
                tbd = len(tb[tb['完成标记']=='已完成'])
                team_detail.append({
                    'team': team, 'batch': batch, 'system': st,
                    'total': len(tb), 'done': tbd, 'undone': len(tb)-tbd,
                    'comp_rate': pct(tbd, len(tb)), 'days': int(tb['人天数值'].sum()),
                })

    # === 模块×批次×系统类型 ===
    module_detail = []
    for mod in sorted(df['模块'].unique()):
        for batch in BATCHES:
            for st in ['JAVA-专业系统','SAP']:
                mb = df[(df['模块']==mod)&(df['批次']==batch)&(df['系统类型']==st)]
                if len(mb)==0: continue
                mbd = len(mb[mb['完成标记']=='已完成'])
                module_detail.append({
                    'module': mod, 'batch': batch, 'system': st,
                    'total': len(mb), 'done': mbd, 'undone': len(mb)-mbd,
                    'comp_rate': pct(mbd, len(mb)), 'days': int(mb['人天数值'].sum()),
                })

    # === 未完成任务明细（三维度）===
    undone_detail = []
    for _, row in undone_df.iterrows():
        undone_detail.append({
            'project': str(row.get('项目','')), 'batch': str(row.get('批次','')),
            'system': str(row.get('系统类型','')), 'module': str(row.get('模块','')),
            'task': str(row.get('任务名称',''))[:60], 'type': str(row.get('任务类型','')),
            'priority': str(row.get('优先级','')), 'status': str(row.get('状态_标准','')),
            'person': str(row.get('负责人','')), 'progress': str(row.get('进度','')),
            'days': row['人天数值'],
        })

    # === 阶段漏斗 ===
    stage_cols = [
        ('FS-功能说明书','FS状态_标准'),
        ('业务测试','业务测试状态_标准'),
        ('TS-技术说明书','TS状态_标准'),
    ]
    stage_funnel = []
    for name, col in stage_cols:
        if col not in df.columns: continue
        valid = df[~df[col].isin(['-','不适用',''])]
        done_valid = done_df[~done_df[col].isin(['-','不适用',''])]
        undone_valid = undone_df[~undone_df[col].isin(['-','不适用',''])]
        stage_funnel.append({
            'stage': name,
            'all_total': len(valid), 'all_done': int(len(valid[valid=='已完成'])),
            'all_rate': pct(len(valid[valid=='已完成']), len(valid)),
            'done_total': len(done_valid), 'done_finished': int(len(done_valid[done_valid=='已完成'])),
            'done_rate': pct(len(done_valid[done_valid=='已完成']), len(done_valid)),
            'undone_total': len(undone_valid), 'undone_finished': int(len(undone_valid[undone_valid=='已完成'])),
            'undone_rate': pct(len(undone_valid[undone_valid=='已完成']), len(undone_valid)),
            'undone_pending': int(len(undone_valid[undone_valid.isin(['待处理','进行中'])])),
        })

    # === 必填字段完整度（按批次×系统类型）===
    df['_filled_count'] = df.apply(lambda row: sum(1 for f in REQUIRED_FIELDS if f in df.columns and is_filled(row[f])), axis=1)
    df['_completeness'] = df['_filled_count'] / len(REQUIRED_FIELDS) * 100

    field_comp_all = []
    for field in REQUIRED_FIELDS:
        if field not in df.columns: continue
        filled = df[field].apply(is_filled).sum()
        field_comp_all.append({'field': field, 'filled': int(filled), 'missing': total-int(filled), 'rate': pct(filled, total)})

    batch_system_field_comp = []
    for batch in BATCHES:
        for st in ['JAVA-专业系统','SAP']:
            bf = df[(df['批次']==batch)&(df['系统类型']==st)]
            if len(bf)==0: continue
            batch_system_field_comp.append({
                'batch': batch, 'system': st, 'total': len(bf),
                'avg_rate': round(bf['_completeness'].mean(), 1),
                'perfect': int(len(bf[bf['_completeness']==100])),
                'perfect_rate': pct(len(bf[bf['_completeness']==100]), len(bf)),
            })

    # 未完成任务必填字段问题
    undone_field_issues = []
    for _, row in undone_df.iterrows():
        missing = [f for f in REQUIRED_FIELDS if f in df.columns and not is_filled(row[f])]
        if missing:
            undone_field_issues.append({
                'project': str(row.get('项目','')), 'batch': str(row.get('批次','')),
                'system': str(row.get('系统类型','')),
                'task': str(row.get('任务名称',''))[:60], 'status': str(row.get('状态_标准','')),
                'person': str(row.get('负责人','')),
                'missing_count': len(missing), 'missing_fields': ', '.join(missing),
            })
    undone_field_issues.sort(key=lambda x: x['missing_count'], reverse=True)

    # === 月度趋势 ===
    monthly_detail = []
    if '结束日期_dt' in df.columns and df['结束日期_dt'].notna().any():
        monthly = df.groupby(df['结束日期_dt'].dt.to_period('M').astype(str)).agg(
            完成任务=('完成标记',lambda x: (x=='已完成').sum()),
            总任务=('状态_标准','count'),
        ).reset_index()
        monthly.columns = ['month','done','total']
        monthly['rate'] = (monthly['done']/monthly['total']*100).round(1)
        monthly_detail = monthly.to_dict('records')

    # === 批次上线时间节点 ===
    BATCH_DEADLINES = {
        'A批次': {'上线': pd.Timestamp('2026-07-31'), '开发截止': pd.Timestamp('2026-06-30')},
        'B批次': {'上线': pd.Timestamp('2026-08-30'), '开发截止': pd.Timestamp('2026-07-30')},
        'C批次': {'上线': pd.Timestamp('2026-10-30'), '开发截止': pd.Timestamp('2026-09-30')},
    }
    deadline_analysis = []
    for batch, dls in BATCH_DEADLINES.items():
        bdf = df[(df['批次']==batch) & df['结束日期_dt'].notna()]
        if len(bdf) == 0: continue
        dev_dl = dls['开发截止']
        # 未完成且超开发截止
        not_closed_b = ~bdf['状态_标准'].isin(['已完成','已取消'])
        over_dev = bdf[not_closed_b & (bdf['结束日期_dt'] > dev_dl)]
        # 已完成但超开发截止
        done_late = bdf[(bdf['状态_标准']=='已完成') & (bdf['结束日期_dt'] > dev_dl)]
        # 距开发截止还有多少天
        days_to_dl = (dev_dl - report_date).days
        deadline_analysis.append({
            'batch': batch,
            'go_live': dls['上线'].strftime('%Y/%m/%d'),
            'dev_deadline': dev_dl.strftime('%Y/%m/%d'),
            'days_left': days_to_dl,
            'total': len(bdf),
            'done': int(len(bdf[bdf['状态_标准']=='已完成'])),
            'done_rate': pct(len(bdf[bdf['状态_标准']=='已完成']), len(bdf)),
            'over_dev': len(over_dev),
            'done_late': len(done_late),
            'urgent': days_to_dl <= 7 and days_to_dl >= 0,
            'past_due': days_to_dl < 0,
        })

    # === 已完成任务验收就绪分析 ===
    acceptance = []
    for _, row in done_df.iterrows():
        tests = []
        for tc in ['系统测试报告','集成测试报告','回归测试报告']:
            if tc in df.columns:
                v = str(row.get(tc,''))
                tests.append(v not in ['','-','nan','None'])
        bt_status = str(row.get('业务测试状态_标准',''))
        bt_start = str(row.get('业务测试实际开始日期',''))
        bt_end = str(row.get('业务测试实际结束日期',''))
        bt_ok = bt_status in ['已完成'] and bt_start not in ['','-','nan','None'] and bt_end not in ['','-','nan','None']
        test_count = sum(tests)
        acceptance.append({
            'project': str(row.get('项目','')), 'batch': str(row.get('批次','')),
            'system': str(row.get('系统类型','')), 'module': str(row.get('模块','')),
            'task': str(row.get('任务名称',''))[:60],
            'type': str(row.get('任务类型','')), 'person': str(row.get('负责人','')),
            'end_date': str(row.get('结束日期','')),
            'bt_status': bt_status,
            'bt_start': bt_start if bt_start not in ['-','nan',''] else '（未填）',
            'bt_end': bt_end if bt_end not in ['-','nan',''] else '（未填）',
            'sys_test': '✅' if (len(tests)>0 and tests[0]) else '❌',
            'integ_test': '✅' if (len(tests)>1 and tests[1]) else '❌',
            'regr_test': '✅' if (len(tests)>2 and tests[2]) else '❌',
            'test_count': test_count,
            'all_ready': test_count == 3 and bt_ok,
        })

    # 验收汇总（按项目×批次×系统）
    acc_summary = []
    for proj in sorted(df['项目'].unique()):
        pacc = [a for a in acceptance if a['project']==proj]
        if not pacc: continue
        batch = pacc[0]['batch']
        syst = pacc[0]['system']
        acc_summary.append({
            'project': proj, 'batch': batch, 'system': syst,
            'total_done': len(pacc),
            'bt_complete': sum(1 for a in pacc if a['bt_status']=='已完成'),
            'sys_test_ok': sum(1 for a in pacc if a['sys_test']=='✅'),
            'integ_test_ok': sum(1 for a in pacc if a['integ_test']=='✅'),
            'regr_test_ok': sum(1 for a in pacc if a['regr_test']=='✅'),
            'all_ready': sum(1 for a in pacc if a['all_ready']),
            'ready_rate': pct(sum(1 for a in pacc if a['all_ready']), len(pacc)),
        })

    # === 延期任务详情（含延期原因和备注）===
    delayed_detail = []
    for item in overdue_list:
        orig = df[(df['项目']==item['project'])&(df['任务名称'].str[:30]==item['task'][:30])]
        if len(orig) > 0:
            row = orig.iloc[0]
            item['reason'] = str(row.get('延期原因','')) if pd.notna(row.get('延期原因','')) and str(row.get('延期原因','')) not in ['-','nan'] else '（未填写）'
            item['remark'] = str(row.get('备注','')) if pd.notna(row.get('备注','')) and str(row.get('备注','')) not in ['-','nan'] else '（无备注）'
        else:
            item['reason'] = '（未填写）'
            item['remark'] = '（无备注）'
        delayed_detail.append(item)
    # 也加入临期任务的延期原因
    for item in near_due_list:
        orig = df[(df['项目']==item['project'])&(df['任务名称'].str[:30]==item['task'][:30])]
        if len(orig) > 0:
            row = orig.iloc[0]
            item['reason'] = str(row.get('延期原因','')) if pd.notna(row.get('延期原因','')) and str(row.get('延期原因','')) not in ['-','nan'] else '（未填写）'
            item['remark'] = str(row.get('备注','')) if pd.notna(row.get('备注','')) and str(row.get('备注','')) not in ['-','nan'] else '（无备注）'
        else:
            item['reason'] = '（未填写）'
            item['remark'] = '（无备注）'

    return {
        'report_date': report_date_str, 'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'kpi': kpi, 'overdue_list': delayed_detail, 'near_due_list': near_due_list,
        'proj_ranking': proj_ranking,
        'batch_kpi': batch_kpi, 'system_kpi': system_kpi, 'batch_system': batch_system,
        'team_detail': team_detail, 'module_detail': module_detail,
        'undone_detail': undone_detail, 'stage_funnel': stage_funnel,
        'field_comp_all': field_comp_all, 'batch_system_field_comp': batch_system_field_comp,
        'undone_field_issues': undone_field_issues[:50],
        'monthly_detail': monthly_detail,
        'deadline_analysis': deadline_analysis,
        'acceptance': acceptance, 'acc_summary': acc_summary,
        'batches': BATCHES, 'REQUIRED_FIELDS': REQUIRED_FIELDS, 'required_count': len(REQUIRED_FIELDS),
    }


def task_row(row, report_date, days_diff, tag):
    return {
        'project': str(row.get('项目','')), 'batch': str(row.get('批次','')),
        'system': str(row.get('系统类型','')), 'module': str(row.get('模块','')),
        'task': str(row.get('任务名称',''))[:80], 'type': str(row.get('任务类型','')),
        'priority': str(row.get('优先级','')), 'status': str(row.get('状态_标准','')),
        'person': str(row.get('负责人','')), 'progress': str(row.get('进度','')),
        'start': str(row.get('开始日期','')), 'end': str(row.get('结束日期','')),
        'days_diff': days_diff, 'tag': tag,
        'reason': str(row.get('延期原因','')) if pd.notna(row.get('延期原因','')) and str(row.get('延期原因','')) not in ['-','nan'] else '（未填写）',
    }


# ============================================================
# CSS
# ============================================================
CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;background:#f0f2f5;color:#333;line-height:1.6}
.header{background:linear-gradient(135deg,#1a3a5c 0%,#2d6a9f 100%);color:#fff;padding:30px 40px}
.header h1{font-size:28px;margin-bottom:5px}
.header .sub{font-size:14px;opacity:.85}
.container{max-width:1500px;margin:0 auto;padding:20px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}
.kpi-card{background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}
.kpi-card .label{font-size:13px;color:#666;margin-bottom:5px}
.kpi-card .value{font-size:30px;font-weight:700}
.kpi-card.green .value{color:#16a34a}
.kpi-card.blue .value{color:#2563eb}
.kpi-card.orange .value{color:#d97706}
.kpi-card.red .value{color:#dc2626}
.kpi-card.gray .value{color:#6b7280}
.kpi-card.purple .value{color:#7c3aed}
.section{background:#fff;border-radius:12px;padding:25px;margin:20px 0;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.section h2{font-size:20px;color:#1a3a5c;border-left:4px solid #2563eb;padding-left:12px;margin-bottom:20px}
.section h3{font-size:16px;color:#374151;margin:20px 0 12px}
.table-wrap{overflow-x:auto;max-height:600px;overflow-y:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#1a3a5c;color:#fff;padding:8px 6px;text-align:center;font-weight:600;white-space:nowrap;position:sticky;top:0;z-index:1}
td{padding:6px;text-align:center;border-bottom:1px solid #e5e7eb}
tr:hover{background:#f8fafc}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
.badge-green{background:#dcfce7;color:#16a34a}
.badge-red{background:#fee2e2;color:#dc2626}
.badge-yellow{background:#fef3c7;color:#d97706}
.badge-blue{background:#dbeafe;color:#2563eb}
.badge-gray{background:#f3f4f6;color:#6b7280}
.badge-purple{background:#ede9fe;color:#7c3aed}
.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}
.chart-box{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.chart-box h3{font-size:15px;color:#374151;margin-bottom:15px}
.chart-box canvas{max-height:300px}
.alert{padding:12px 16px;border-radius:8px;margin:10px 0;font-size:13px}
.alert-warn{background:#fef3c7;border:1px solid #fcd34d;color:#92400e}
.alert-info{background:#dbeafe;border:1px solid #93c5fd;color:#1e40af}
.alert-danger{background:#fee2e2;border:1px solid #fca5a5;color:#991b1b}
.footer{text-align:center;padding:20px;color:#9ca3af;font-size:12px}
@media(max-width:768px){.chart-row{grid-template-columns:1fr}}
.dim-tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;margin:0 2px}
.dim-project{background:#dbeafe;color:#1e40af}
.dim-batch{background:#dcfce7;color:#166534}
.dim-system{background:#ede9fe;color:#6b21a8}"""


# ============================================================
# HTML 生成
# ============================================================
def generate_html(d, output_path):
    P = []  # parts
    P.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">')
    P.append('<title>1455项目 PMO监控分析报告</title>')
    P.append('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>')
    P.append('<style>' + CSS + '</style>\n</head>\n<body>')
    P.append('<div class="header"><h1>1455项目 — PMO项目监控分析报告</h1>')
    P.append(f'<div class="sub">数据截止: {d["report_date"]} | 报告生成: {d["generated_at"]} | A/B/C批次 | JAVA-专业系统 / SAP</div></div>')
    P.append('<div class="container">')

    # ===== KPI =====
    k = d['kpi']
    P.append('<div class="kpi-grid">')
    for label, val, cls in [
        ('总任务数', k['total'], 'blue'), ('已完成', k['done'], 'green'),
        ('完成率', f"{k['comp_rate']}%", 'green'), ('未完成', k['undone'], 'orange'),
        ('总人天', str(k['total_days']), 'blue'), ('⚠️ 逾期', str(k['overdue']), 'red'),
        ('⏰ 临期预警', str(k['near_due']), 'purple'), ('项目标段', str(k['projects']), 'gray'),
    ]:
        P.append(f'<div class="kpi-card {cls}"><div class="label">{label}</div><div class="value">{val}</div></div>')
    P.append('</div>')

    # ===== 逾期任务（最顶部）=====
    _render_risk_section(P, d, 'overdue_list', '逾期任务 — 请优先沟通处理', 
        '以下任务计划结束日期已过但仍未完成。延期原因多数未填写，建议逐条确认。', '#dc2626', '#fff5f5', '已逾期')
    # ===== 临期任务 =====
    _render_risk_section(P, d, 'near_due_list', '临期预警 — 7天内到期需重点关注',
        f'以下任务将在 {d["report_date"]} 后7天内到期。请确认进度是否能按时完成。', '#d97706', '#fffdf5', '临期')

    # ===== 一、项目完成率排名 =====
    P.append('<div class="section"><h2>一、项目标段完成率排名（批次 × 系统类型）</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>排名</th><th>项目标段</th><th>批次</th><th>系统类型</th><th>总任务</th><th>已完成</th><th>完成率</th><th>人天</th><th>逾期</th><th>临期</th></tr>')
    for i, r in enumerate(d['proj_ranking']):
        rc = 'badge-green' if r['rate']>=90 else ('badge-yellow' if r['rate']>=70 else 'badge-red')
        bc = 'badge-blue' if r['batch']!='未标注批次' else 'badge-gray'
        sc = 'badge-purple' if r['system']=='JAVA-专业系统' else 'badge-blue'
        od_str = f'<span class="badge badge-red">{r["overdue"]}</span>' if r['overdue']>0 else '-'
        nd_str = f'<span class="badge badge-yellow">{r["near_due"]}</span>' if r['near_due']>0 else '-'
        P.append(f'<tr><td>{i+1}</td><td style="text-align:left;font-weight:600">{r["project"]}</td><td><span class="badge {bc}">{r["batch"]}</span></td><td><span class="badge {sc}">{r["system"]}</span></td><td>{r["total"]}</td><td>{r["done"]}</td><td><span class="badge {rc}">{r["rate"]}%</span></td><td>{r["days"]}</td><td>{od_str}</td><td>{nd_str}</td></tr>')
    P.append('</table></div></div>')

    # ===== 二、批次 × 系统类型 总览 =====
    P.append('<div class="section"><h2>二、批次 × 系统类型 总览</h2>')
    P.append('<div class="chart-row"><div class="chart-box"><h3>各批次任务分布</h3><canvas id="batchBarChart"></canvas></div>')
    P.append('<div class="chart-box"><h3>系统类型分布</h3><canvas id="sysPieChart"></canvas></div></div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>系统类型</th><th>总任务</th><th>已完成</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
    for r in d['batch_system']:
        rc = 'badge-green' if r['comp_rate']>=90 else ('badge-yellow' if r['comp_rate']>=70 else 'badge-red')
        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 三、未完成任务明细 =====
    undone = d['undone_detail']
    P.append(f'<div class="section" style="border-left:4px solid #dc2626"><h2>三、未完成任务明细（{len(undone)}条）— 项目 × 批次 × 系统类型</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务名称</th><th>类型</th><th>优先级</th><th>状态</th><th>负责人</th><th>进度</th></tr>')
    for r in undone:
        pc = 'badge-red' if r['priority']=='高' else ('badge-yellow' if r['priority']=='中' else 'badge-gray')
        P.append(f'<tr><td style="text-align:left">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["module"]}</td><td style="text-align:left;max-width:250px">{r["task"]}</td><td>{r["type"]}</td><td><span class="badge {pc}">{r["priority"]}</span></td><td>{r["status"]}</td><td>{r["person"]}</td><td>{r["progress"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 四、供应商×批次×系统类型 =====
    P.append('<div class="section"><h2>四、供应商团队绩效 — 批次 × 系统类型</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>供应商</th><th>批次</th><th>系统</th><th>总任务</th><th>已完成</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
    for r in d['team_detail']:
        rc = 'badge-green' if r['comp_rate']>=90 else ('badge-yellow' if r['comp_rate']>=70 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{r["team"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 五、模块×批次×系统类型 =====
    P.append('<div class="section"><h2>五、模块完成率明细 — 批次 × 系统类型</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>模块</th><th>批次</th><th>系统</th><th>总任务</th><th>已完成</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
    for r in d['module_detail']:
        rc = 'badge-green' if r['comp_rate']>=90 else ('badge-yellow' if r['comp_rate']>=70 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{r["module"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 六、阶段漏斗 =====
    P.append('<div class="section"><h2>六、FS → 业务测试 → TS 阶段漏斗</h2>')
    P.append('<div class="chart-row"><div class="chart-box"><h3>全部任务</h3><canvas id="stageAllChart"></canvas></div>')
    P.append('<div class="chart-box"><h3>已完成 vs 未完成</h3><canvas id="stageDoneChart"></canvas></div></div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>阶段</th><th>全部</th><th>全部完成率</th><th>已完成任务-完成率</th><th>未完成-待办</th></tr>')
    for s in d['stage_funnel']:
        P.append(f'<tr><td><strong>{s["stage"]}</strong></td><td>{s["all_total"]}</td><td><span class="badge badge-blue">{s["all_rate"]}%</span></td><td><span class="badge badge-green">{s["done_rate"]}%</span></td><td><span class="badge badge-yellow">{s["undone_pending"]}</span></td></tr>')
    P.append('</table></div></div>')

    # ===== 七、必填字段完整度 =====
    P.append('<div class="section" style="border-left:4px solid #d97706"><h2>七、必填字段完整度 — 批次 × 系统类型</h2>')
    P.append(f'<div class="alert alert-warn">模板定义 <strong>{d["required_count"]} 个必填字段</strong>（★必填）。</div>')
    P.append('<h3>7.1 各字段填写率</h3><div class="table-wrap"><table>')
    P.append('<tr><th>字段名</th><th>已填写</th><th>缺失</th><th>完整度</th></tr>')
    for f in sorted(d['field_comp_all'], key=lambda x: x['rate']):
        rc = 'badge-green' if f['rate']>=95 else ('badge-yellow' if f['rate']>=80 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{f["field"]}</td><td>{f["filled"]}</td><td><span class="badge badge-red">{f["missing"]}</span></td><td><span class="badge {rc}">{f["rate"]}%</span></td></tr>')
    P.append('</table></div>')
    P.append('<h3>7.2 批次×系统类型 完整度</h3><div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>系统</th><th>总任务</th><th>平均完整率</th><th>100%完整记录</th><th>100%占比</th></tr>')
    for r in d['batch_system_field_comp']:
        rc = 'badge-green' if r['avg_rate']>=95 else ('badge-yellow' if r['avg_rate']>=80 else 'badge-red')
        P.append(f'<tr><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td><span class="badge {rc}">{r["avg_rate"]}%</span></td><td>{r["perfect"]}</td><td>{r["perfect_rate"]}%</td></tr>')
    P.append('</table></div>')
    if d['undone_field_issues']:
        P.append('<h3>7.3 未完成任务必填字段缺失 Top 50</h3><div class="table-wrap"><table>')
        P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>任务</th><th>状态</th><th>负责人</th><th>缺失数</th><th>缺失字段</th></tr>')
        for i, iss in enumerate(d['undone_field_issues']):
            mc = 'badge-red' if iss['missing_count']>=5 else 'badge-yellow'
            P.append(f'<tr><td>{i+1}</td><td style="text-align:left">{iss["project"]}</td><td>{iss["batch"]}</td><td>{iss["system"]}</td><td style="text-align:left;max-width:250px">{iss["task"]}</td><td>{iss["status"]}</td><td>{iss["person"]}</td><td><span class="badge {mc}">{iss["missing_count"]}</span></td><td style="text-align:left;font-size:11px">{iss["missing_fields"]}</td></tr>')
        P.append('</table></div>')
    P.append('</div>')

    # ===== 八、批次上线时间节点 =====
    P.append('<div class="section" style="border-left:4px solid #7c3aed"><h2>八、批次上线时间节点 & 开发截止预警</h2>')
    P.append('<div class="alert alert-info">上线时间：A批次 7/31、B批次 8/30、C批次 10/30。开发任务需提前1个月完成。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>上线日期</th><th>开发截止</th><th>距截止</th><th>总任务</th><th>已完成</th><th>完成率</th><th>超截止未完成</th><th>已完成但超截止</th><th>状态</th></tr>')
    for r in d['deadline_analysis']:
        rc = 'badge-green' if r['done_rate']>=90 else ('badge-yellow' if r['done_rate']>=70 else 'badge-red')
        if r['past_due']:
            dl_str = f'<span class="badge badge-red">已超期{-r["days_left"]}天</span>'
            st_str = '<span class="badge badge-red">🔴 已超开发截止</span>'
        elif r['urgent']:
            dl_str = f'<span class="badge badge-yellow">仅剩{r["days_left"]}天</span>'
            st_str = '<span class="badge badge-yellow">🟡 即将截止</span>'
        else:
            dl_str = f'<span class="badge badge-green">还剩{r["days_left"]}天</span>'
            st_str = '<span class="badge badge-green">🟢 正常</span>'
        od_str = f'<span class="badge badge-red">{r["over_dev"]}</span>' if r['over_dev']>0 else '-'
        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["go_live"]}</td><td style="font-weight:600">{r["dev_deadline"]}</td><td>{dl_str}</td><td>{r["total"]}</td><td>{r["done"]}</td><td><span class="badge {rc}">{r["done_rate"]}%</span></td><td>{od_str}</td><td>{r["done_late"]}</td><td>{st_str}</td></tr>')
    P.append('</table></div></div>')

    # ===== 九、已完成任务验收就绪分析 =====
    P.append('<div class="section" style="border-left:4px solid #16a34a"><h2>九、已完成任务验收就绪分析 — 测试报告 & 业务测试</h2>')
    P.append('<div class="alert alert-info">验收需关注：业务测试状态、系统测试报告、集成测试报告、回归测试报告。</div>')

    # 汇总
    P.append('<h3>9.1 各项目验收就绪汇总（项目×批次×系统）</h3>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>已完成</th><th>业务测试完成</th><th>系统测试✅</th><th>集成测试✅</th><th>回归测试✅</th><th>全部就绪</th><th>就绪率</th></tr>')
    for r in d['acc_summary']:
        rc = 'badge-green' if r['ready_rate']>=80 else ('badge-yellow' if r['ready_rate']>=50 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total_done"]}</td><td>{r["bt_complete"]}</td><td>{r["sys_test_ok"]}</td><td>{r["integ_test_ok"]}</td><td>{r["regr_test_ok"]}</td><td>{r["all_ready"]}</td><td><span class="badge {rc}">{r["ready_rate"]}%</span></td></tr>')
    P.append('</table></div>')

    # 验收不全的任务
    acc_incomplete = [a for a in d['acceptance'] if not a['all_ready']]
    P.append(f'<h3>9.2 验收材料不全的已完成任务（{len(acc_incomplete)}条，需补充）</h3>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>结束日期</th><th>业务测试</th><th>系统测试</th><th>集成测试</th><th>回归测试</th><th>缺失项</th></tr>')
    for a in acc_incomplete[:100]:
        missing = []
        if a['bt_status'] != '已完成': missing.append('业务测试')
        if a['sys_test'] == '❌': missing.append('系统测试报告')
        if a['integ_test'] == '❌': missing.append('集成测试报告')
        if a['regr_test'] == '❌': missing.append('回归测试报告')
        P.append(f'<tr><td style="text-align:left">{a["project"]}</td><td>{a["batch"]}</td><td>{a["system"]}</td><td>{a["module"]}</td><td style="text-align:left;max-width:200px">{a["task"]}</td><td>{a["end_date"]}</td><td>{a["bt_status"]}</td><td>{a["sys_test"]}</td><td>{a["integ_test"]}</td><td>{a["regr_test"]}</td><td style="text-align:left;font-size:11px">{", ".join(missing)}</td></tr>')
    if len(acc_incomplete) > 100:
        P.append(f'<tr><td colspan="11" style="color:#666">... 还有 {len(acc_incomplete)-100} 条</td></tr>')
    P.append('</table></div></div>')

    # ===== 十、延期/临期任务 — 延期原因 & 备注 =====
    P.append('<div class="section" style="border-left:4px solid #dc2626"><h2>十、逾期 & 临期任务 — 延期原因与备注</h2>')
    P.append('<div class="alert alert-danger">以下为逾期+临期任务，重点关注延期原因是否已填写、备注是否有说明。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>类型</th><th>项目</th><th>批次</th><th>系统</th><th>任务</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>延期原因</th><th>备注</th></tr>')
    all_risk = [(item, '🔴逾期') for item in d['overdue_list']] + [(item, '🟡临期') for item in d['near_due_list']]
    for item, tag in all_risk:
        reason = item.get('reason','（未填写）')
        remark = item.get('remark','（无备注）')
        reason_cls = 'color:#dc2626;font-weight:600' if reason == '（未填写）' else ''
        remark_cls = 'color:#9ca3af' if remark == '（无备注）' else ''
        diff = item.get('days_diff',0)
        if item.get('tag')=='逾期':
            diff_str = f'+{diff}天'
        else:
            diff_str = f'{diff}天'
        P.append(f'<tr><td>{tag}</td><td style="text-align:left">{item["project"]}</td><td>{item["batch"]}</td><td>{item["system"]}</td><td style="text-align:left;max-width:200px">{item["task"]}</td><td>{item["status"]}</td><td>{item["person"]}</td><td>{item["end"]} ({diff_str})</td><td>{item["progress"]}</td><td style="text-align:left;font-size:11px;{reason_cls}">{reason}</td><td style="text-align:left;font-size:11px;{remark_cls}">{remark}</td></tr>')
    P.append('</table></div>')
    reason_ok = sum(1 for item,_ in all_risk if item.get('reason','（未填写）') not in ['（未填写）','-',''])
    remark_ok = sum(1 for item,_ in all_risk if item.get('remark','（无备注）') not in ['（无备注）','-',''])
    P.append(f'<div style="margin-top:10px;font-size:13px;color:#666">延期原因填写率: {reason_ok}/{len(all_risk)} | 备注填写率: {remark_ok}/{len(all_risk)}</div></div>')

    # ===== 十一、月度趋势 =====
    if d['monthly_detail']:
        P.append('<div class="section"><h2>十一、月度完成趋势</h2><div class="chart-box"><canvas id="monthlyChart"></canvas></div></div>')

    P.append(f'<div class="footer"><p>1455项目 PMO监控分析报告 | 自动生成于 {d["generated_at"]} | 数据截止 {d["report_date"]}</p><p>逾期判断：结束日期 < {d["report_date"]} 且未完成 | 临期：{d["report_date"]}后7天内到期</p></div></div>')

    # ===== Charts JS =====
    batch_labels = json.dumps([b['batch'] for b in d['batch_kpi']])
    batch_done = json.dumps([b['done'] for b in d['batch_kpi']])
    batch_undone = json.dumps([b['undone'] for b in d['batch_kpi']])
    sys_labels = json.dumps([s['system'] for s in d['system_kpi']])
    sys_totals = json.dumps([s['total'] for s in d['system_kpi']])
    stage_labels = json.dumps([s['stage'] for s in d['stage_funnel']])
    stage_all = json.dumps([s['all_rate'] for s in d['stage_funnel']])
    stage_done = json.dumps([s['done_rate'] for s in d['stage_funnel']])
    stage_undone = json.dumps([s['undone_rate'] for s in d['stage_funnel']])

    P.append(f'''<script>
new Chart(document.getElementById('batchBarChart'),{{type:'bar',data:{{labels:{batch_labels},datasets:[{{label:'已完成',data:{batch_done},backgroundColor:'#16a34a'}},{{label:'未完成',data:{batch_undone},backgroundColor:'#ef4444'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{stacked:true}},y:{{stacked:true}}}}}}}});
new Chart(document.getElementById('sysPieChart'),{{type:'doughnut',data:{{labels:{sys_labels},datasets:[{{data:{sys_totals},backgroundColor:['#7c3aed','#2563eb']}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('stageAllChart'),{{type:'bar',data:{{labels:{stage_labels},datasets:[{{label:'完成率(%)',data:{stage_all},backgroundColor:'#2563eb'}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{min:0,max:100}}}}}}}});
new Chart(document.getElementById('stageDoneChart'),{{type:'bar',data:{{labels:{stage_labels},datasets:[{{label:'已完成任务中',data:{stage_done},backgroundColor:'#16a34a'}},{{label:'未完成任务中',data:{stage_undone},backgroundColor:'#ef4444'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{min:0,max:100}}}}}}}});
''')

    if d['monthly_detail']:
        ml = json.dumps([m['month'] for m in d['monthly_detail']])
        md = json.dumps([m['done'] for m in d['monthly_detail']])
        mt = json.dumps([m['total'] for m in d['monthly_detail']])
        P.append(f'''new Chart(document.getElementById('monthlyChart'),{{type:'line',data:{{labels:{ml},datasets:[{{label:'完成任务',data:{md},borderColor:'#16a34a',backgroundColor:'rgba(22,163,74,.1)',fill:true,tension:.3}},{{label:'总任务',data:{mt},borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.1)',fill:true,tension:.3}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
''')

    P.append('</script></body></html>')
    html = '\n'.join(P)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path


def _render_risk_section(P, d, list_key, title, desc, border_color, bg_color, tag_label):
    items = d.get(list_key, [])
    if not items:
        P.append(f'<div class="section" style="border-left:4px solid {border_color}; background:{bg_color}">')
        P.append(f'<h2 style="color:{border_color}">{title}（0条）</h2>')
        P.append(f'<div class="alert alert-info">✅ 当前无{tag_label}任务</div></div>')
        return
    P.append(f'<div class="section" style="border-left:4px solid {border_color}; background:{bg_color}">')
    P.append(f'<h2 style="color:{border_color}">{title}（{len(items)}条）</h2>')
    P.append(f'<div class="alert alert-danger">{desc}</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务名称</th><th>类型</th><th>优先级</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>延期原因</th></tr>')
    for i, item in enumerate(items):
        diff = item.get('days_diff', 0)
        if item.get('tag') == '逾期':
            diff_str = f'<span style="color:#dc2626;font-weight:700">+{diff}天</span>'
        else:
            diff_str = f'<span style="color:#d97706;font-weight:700">{diff}天</span>'
        pc = 'badge-red' if item['priority']=='高' else ('badge-yellow' if item['priority']=='中' else 'badge-gray')
        P.append(f'<tr><td><strong>{i+1}</strong></td><td style="text-align:left">{item["project"]}</td><td>{item["batch"]}</td><td>{item["system"]}</td><td>{item["module"]}</td><td style="text-align:left;max-width:250px">{item["task"]}</td><td>{item["type"]}</td><td><span class="badge {pc}">{item["priority"]}</span></td><td>{item["status"]}</td><td>{item["person"]}</td><td>{item["end"]} {diff_str}</td><td>{item["progress"]}</td><td style="text-align:left;font-size:11px">{item["reason"]}</td></tr>')
    P.append('</table></div>')
    # 汇总
    proj_c = Counter(item['project'] for item in items)
    batch_c = Counter(item['batch'] for item in items)
    sys_c = Counter(item['system'] for item in items)
    P.append('<div style="margin-top:10px;font-size:13px;color:#666">')
    P.append(f'📌 涉及项目: {", ".join(f"{k}({v})" for k,v in proj_c.most_common())} | ')
    P.append(f'批次: {", ".join(f"{k}({v})" for k,v in batch_c.most_common())} | ')
    P.append(f'系统: {", ".join(f"{k}({v})" for k,v in sys_c.most_common())} | ')
    reason_filled = sum(1 for item in items if item['reason'] not in ['（未填写）','-',''])
    P.append(f'延期原因填写: {reason_filled}/{len(items)}')
    P.append('</div></div>')


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='PMO项目监控分析工具')
    parser.add_argument('input', help='输入Excel文件路径')
    parser.add_argument('-o', '--output', default=None, help='输出HTML文件路径')
    parser.add_argument('-d', '--date', default=None, help='报告日期, 如 2026/7/22 (默认取数据中最晚结束日期)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'❌ 文件不存在: {args.input}'); sys.exit(1)

    print(f'📊 正在分析: {args.input}')
    df = load_and_clean(args.input)
    print(f'   数据: {len(df)}行, 批次: {df["批次"].nunique()}, JAVA: {len(df[df["系统类型"]=="JAVA-专业系统"])}, SAP: {len(df[df["系统类型"]=="SAP"])}')

    # 报告日期：默认使用今天，用户可指定
    report_date = args.date if args.date else pd.Timestamp.now().strftime('%Y/%m/%d')
    print(f'   报告日期: {report_date}')

    if args.output is None:
        base = os.path.splitext(os.path.basename(args.input))[0]
        date_str = pd.Timestamp(report_date).strftime('%Y%m%d')
        os.makedirs('outputs', exist_ok=True)
        args.output = os.path.join('outputs', f'{base}_PMO监控分析报告_{date_str}.html')

    print('   计算统计指标...')
    data = compute_all_stats(df, report_date)
    print(f'   逾期: {data["kpi"]["overdue"]}条, 临期: {data["kpi"]["near_due"]}条, 未完成: {data["kpi"]["undone"]}条')
    print('   生成HTML报告...')
    generate_html(data, args.output)
    print(f'✅ 报告已生成: {args.output}')


if __name__ == '__main__':
    main()
