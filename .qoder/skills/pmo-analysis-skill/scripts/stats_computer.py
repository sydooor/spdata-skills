"""PMO 项目监控分析 — 统计指标计算"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
from config import BATCHES, SYSTEM_TYPES, BATCH_DEADLINES, BPC_DEADLINE, BPC_BATCH_LABEL, NEAR_DUE_DAYS, REQUIRED_FIELDS, SAP_ONLY_FIELDS, JAVA_ONLY_FIELDS, SAP_TS_CONDITIONAL_FIELDS
from data_loader import pct, is_filled


def task_row(row, report_date, days_diff, tag):
    """构造逾期/临期任务行"""
    return {
        'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
        'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
        'task': str(row.get('任务名称', ''))[:80], 'desc': str(row.get('描述', ''))[:80], 'type': str(row.get('任务类型', '')),
        'priority': str(row.get('优先级', '')), 'status': str(row.get('状态_标准', '')),
        'person': str(row.get('负责人', '')), 'progress': str(row.get('进度', '')),
        'start': str(row.get('开始日期', '')), 'end': str(row.get('结束日期', '')),
        'days_diff': days_diff, 'tag': tag,
        'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因', '')) and str(row.get('延期原因', '')) not in ['-', 'nan'] else '（未填写）',
        'fs_status': str(row.get('FS状态_标准', '-')),
        'bt_status': str(row.get('业务测试状态_标准', '-')),
        'ts_status': str(row.get('TS状态_标准', '-')),
    }


def bt_task_row(row, report_date, days_diff, tag):
    """构造业务测试逾期/临期任务行"""
    bt_end_dt = row.get('业务测试计划结束日期_dt')
    bt_end_str = bt_end_dt.strftime('%Y/%m/%d') if pd.notna(bt_end_dt) else '-'
    return {
        'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
        'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
        'task': str(row.get('任务名称', ''))[:80], 'type': str(row.get('任务类型', '')),
        'priority': str(row.get('优先级', '')), 'status': str(row.get('状态_标准', '')),
        'person': str(row.get('负责人', '')), 'progress': str(row.get('进度', '')),
        'start': str(row.get('开始日期', '')), 'end': bt_end_str,
        'days_diff': days_diff, 'tag': tag,
        'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因', '')) and str(row.get('延期原因', '')) not in ['-', 'nan'] else '（未填写）',
        'remark': str(row.get('备注', '')) if pd.notna(row.get('备注', '')) and str(row.get('备注', '')) not in ['-', 'nan'] else '（无备注）',
        'fs_status': str(row.get('FS状态_标准', '-')),
        'bt_status': str(row.get('业务测试状态_标准', '-')),
        'ts_status': str(row.get('TS状态_标准', '-')),
        'bt_person': str(row.get('业务测试负责人', '')) if pd.notna(row.get('业务测试负责人')) else '-',
        'bt_plan_end': bt_end_str,
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


def compute_bt_risk(df, report_date):
    """计算业务测试阶段的逾期和临期任务
    条件：业务测试状态 ≠ 已完成，且业务测试计划结束日期已过/临近"""
    bt_overdue_list = []
    bt_near_due_list = []
    if '业务测试计划结束日期_dt' not in df.columns:
        return bt_overdue_list, bt_near_due_list
    not_cancelled = df['完成标记'] != '已取消'
    bt_not_done = df['业务测试状态_标准'] != '已完成'
    odf = df[not_cancelled & bt_not_done & (df['业务测试计划结束日期_dt'] < report_date)]
    ndf = df[not_cancelled & bt_not_done & (df['业务测试计划结束日期_dt'] >= report_date) & (df['业务测试计划结束日期_dt'] <= report_date + timedelta(days=NEAR_DUE_DAYS))]
    for _, row in odf.iterrows():
        days_overdue = (report_date - row['业务测试计划结束日期_dt']).days
        bt_overdue_list.append(bt_task_row(row, report_date, days_overdue, '逾期'))
    for _, row in ndf.iterrows():
        days_left = (row['业务测试计划结束日期_dt'] - report_date).days
        bt_near_due_list.append(bt_task_row(row, report_date, days_left, '临期'))
    return bt_overdue_list, bt_near_due_list


# ============================================================
# 项目完成率排名
# ============================================================
def compute_proj_ranking(df, overdue_list, near_due_list):
    """计算各项目标段完成率排名（分母排除已取消）"""
    proj_ranking = []
    for proj in sorted(df['项目'].unique()):
        pdf = df[df['项目'] == proj]
        pdone = len(pdf[pdf['完成标记'] == '已完成'])
        pcancelled = len(pdf[pdf['完成标记'] == '已取消'])
        batch = pdf['批次'].iloc[0]
        syst = pdf['系统类型'].iloc[0]
        effective_total = len(pdf) - pcancelled
        proj_ranking.append({
            'project': proj, 'batch': batch, 'system': syst,
            'total': len(pdf), 'done': pdone, 'cancelled': pcancelled,
            'undone': len(pdf) - pdone - pcancelled,
            'rate': pct(pdone, effective_total),
            'days': int(pdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['project'] == proj]),
            'near_due': len([x for x in near_due_list if x['project'] == proj]),
        })
    batch_order = {b: i for i, b in enumerate(BATCHES)}
    proj_ranking.sort(key=lambda x: (batch_order.get(x['batch'], 99), -x['rate']))
    return proj_ranking


# ============================================================
# KPI
# ============================================================
def compute_kpi(df, overdue_list, near_due_list):
    """计算核心KPI指标（分母排除已取消）"""
    done_df = df[df['完成标记'] == '已完成']
    undone_df = df[df['完成标记'] == '未完成']
    cancelled_df = df[df['完成标记'] == '已取消']
    effective_total = len(df) - len(cancelled_df)
    return {
        'total': len(df), 'done': len(done_df), 'undone': len(undone_df),
        'cancelled': len(cancelled_df),
        'comp_rate': pct(len(done_df), effective_total),
        'total_days': int(df['人天数值'].sum()),
        'overdue': len(overdue_list), 'near_due': len(near_due_list),
        'projects': int(df['项目'].nunique()), 'modules': int(df['模块'].nunique()),
        'people': int(df['负责人'].nunique()),
    }


# ============================================================
# 批次KPI
# ============================================================
def compute_batch_kpi(df, overdue_list, near_due_list):
    """按批次统计KPI（分母排除已取消）"""
    batch_kpi = []
    for batch in BATCHES:
        bdf = df[df['批次'] == batch]
        bdone = len(bdf[bdf['完成标记'] == '已完成'])
        bcancelled = len(bdf[bdf['完成标记'] == '已取消'])
        effective_total = len(bdf) - bcancelled
        batch_kpi.append({
            'batch': batch, 'total': len(bdf), 'done': bdone, 'cancelled': bcancelled,
            'undone': len(bdf) - bdone - bcancelled,
            'comp_rate': pct(bdone, effective_total), 'days': int(bdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['batch'] == batch]),
            'near_due': len([x for x in near_due_list if x['batch'] == batch]),
            'projects': int(bdf['项目'].nunique()),
        })
    return batch_kpi


# ============================================================
# 系统类型KPI
# ============================================================
def compute_system_kpi(df, overdue_list, near_due_list):
    """按系统类型统计KPI（分母排除已取消）"""
    system_kpi = []
    for st in SYSTEM_TYPES:
        sdf = df[df['系统类型'] == st]
        sd = len(sdf[sdf['完成标记'] == '已完成'])
        scancelled = len(sdf[sdf['完成标记'] == '已取消'])
        effective_total = len(sdf) - scancelled
        system_kpi.append({
            'system': st, 'total': len(sdf), 'done': sd, 'cancelled': scancelled,
            'undone': len(sdf) - sd - scancelled,
            'comp_rate': pct(sd, effective_total), 'days': int(sdf['人天数值'].sum()),
            'overdue': len([x for x in overdue_list if x['system'] == st]),
            'near_due': len([x for x in near_due_list if x['system'] == st]),
            'projects': int(sdf['项目'].nunique()),
        })
    return system_kpi


# ============================================================
# 批次 × 系统类型
# ============================================================
def compute_batch_system(df):
    """批次 × 系统类型交叉统计（分母排除已取消）"""
    batch_system = []
    for batch in BATCHES:
        for st in SYSTEM_TYPES:
            bs = df[(df['批次'] == batch) & (df['系统类型'] == st)]
            if len(bs) == 0:
                continue
            bsd = len(bs[bs['完成标记'] == '已完成'])
            bsc = len(bs[bs['完成标记'] == '已取消'])
            effective_total = len(bs) - bsc
            batch_system.append({
                'batch': batch, 'system': st, 'total': len(bs),
                'done': bsd, 'cancelled': bsc, 'undone': len(bs) - bsd - bsc,
                'comp_rate': pct(bsd, effective_total),
                'days': int(bs['人天数值'].sum()),
            })
    return batch_system


# ============================================================
# 供应商 × 批次 × 系统类型
# ============================================================
def compute_team_detail(df):
    """供应商团队绩效统计（分母排除已取消）"""
    team_detail = []
    for team in sorted(df['供应商团队'].unique()):
        for batch in BATCHES:
            for st in SYSTEM_TYPES:
                tb = df[(df['供应商团队'] == team) & (df['批次'] == batch) & (df['系统类型'] == st)]
                if len(tb) == 0:
                    continue
                tbd = len(tb[tb['完成标记'] == '已完成'])
                tbc = len(tb[tb['完成标记'] == '已取消'])
                effective_total = len(tb) - tbc
                team_detail.append({
                    'team': team, 'batch': batch, 'system': st,
                    'total': len(tb), 'done': tbd, 'cancelled': tbc,
                    'undone': len(tb) - tbd - tbc,
                    'comp_rate': pct(tbd, effective_total), 'days': int(tb['人天数值'].sum()),
                })
    return team_detail


# ============================================================
# 模块 × 批次 × 系统类型
# ============================================================
def compute_module_detail(df):
    """模块完成率明细统计（分母排除已取消）"""
    module_detail = []
    for mod in sorted(df['模块'].unique()):
        for batch in BATCHES:
            for st in SYSTEM_TYPES:
                mb = df[(df['模块'] == mod) & (df['批次'] == batch) & (df['系统类型'] == st)]
                if len(mb) == 0:
                    continue
                mbd = len(mb[mb['完成标记'] == '已完成'])
                mbc = len(mb[mb['完成标记'] == '已取消'])
                effective_total = len(mb) - mbc
                module_detail.append({
                    'module': mod, 'batch': batch, 'system': st,
                    'total': len(mb), 'done': mbd, 'cancelled': mbc,
                    'undone': len(mb) - mbd - mbc,
                    'comp_rate': pct(mbd, effective_total), 'days': int(mb['人天数值'].sum()),
                })
    return module_detail


# ============================================================
# 未完成任务明细
# ============================================================
def compute_undone_detail(df):
    """未完成任务明细表（仅真正未完成，不含已取消）"""
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


def compute_cancelled_detail(df):
    """已取消任务明细表"""
    cancelled_df = df[df['完成标记'] == '已取消']
    cancelled_detail = []
    for _, row in cancelled_df.iterrows():
        cancelled_detail.append({
            'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
            'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
            'task': str(row.get('任务名称', ''))[:60], 'type': str(row.get('任务类型', '')),
            'priority': str(row.get('优先级', '')), 'status': str(row.get('状态_标准', '')),
            'person': str(row.get('负责人', '')), 'progress': str(row.get('进度', '')),
            'days': row['人天数值'],
        })
    return cancelled_detail


# ============================================================
# 阶段卡点分析（替换旧的"阶段漏斗"）
# ============================================================
def compute_phase_blockage(df):
    """各阶段状态分布 + 卡点计数（待处理+进行中 = 阻塞任务）"""
    phases = [
        ('FS阶段', 'FS状态_标准'),
        ('业务测试阶段', '业务测试状态_标准'),
        ('TS阶段', 'TS状态_标准'),
    ]
    blockage = []
    for name, col in phases:
        if col not in df.columns:
            continue
        pending = int(len(df[df[col] == '待处理']))
        in_progress = int(len(df[df[col] == '进行中']))
        done = int(len(df[df[col] == '已完成']))
        na = int(len(df[df[col].isin(['-', '不适用', '', None]) | df[col].isna()]))
        blockage.append({
            'phase': name,
            'pending': pending,
            'in_progress': in_progress,
            'done': done,
            'na': na,
            'blocked': pending + in_progress,
        })
    return blockage


def compute_phase_blockage_by_project(df):
    """按项目统计各阶段卡点任务数，按总卡点降序"""
    phases = [
        ('FS卡点', 'FS状态_标准'),
        ('业务测试卡点', '业务测试状态_标准'),
        ('TS卡点', 'TS状态_标准'),
    ]
    result = []
    for proj in sorted(df['项目'].unique()):
        pdf = df[df['项目'] == proj]
        row = {
            'project': proj,
            'batch': pdf['批次'].iloc[0],
            'system': pdf['系统类型'].iloc[0],
            'total': len(pdf),
        }
        total_blocked = 0
        for name, col in phases:
            if col in df.columns:
                blocked = int(len(pdf[pdf[col].isin(['待处理', '进行中'])]))
                row[name] = blocked
                total_blocked += blocked
        row['total_blocked'] = total_blocked
        result.append(row)
    result.sort(key=lambda x: x['total_blocked'], reverse=True)
    return result


def compute_phase_blockage_by_person(df):
    """按负责人统计各阶段卡点任务，按总卡点降序，取 Top 15"""
    from collections import defaultdict
    person_stats = defaultdict(lambda: {
        'FS_pending': 0, 'FS_in_progress': 0,
        'BT_pending': 0, 'BT_in_progress': 0,
        'TS_pending': 0, 'TS_in_progress': 0,
    })

    for _, row in df.iterrows():
        # FS阶段 — 责任人取 FS负责人 列
        fs_status = str(row.get('FS状态_标准', ''))
        fs_person = str(row.get('FS负责人', ''))
        if fs_status in ['待处理', '进行中'] and fs_person not in ['', '-', 'nan', 'None']:
            key = 'FS_pending' if fs_status == '待处理' else 'FS_in_progress'
            person_stats[fs_person][key] += 1

        # 业务测试阶段 — 责任人取 业务测试负责人 列
        bt_status = str(row.get('业务测试状态_标准', ''))
        bt_person = str(row.get('业务测试负责人', ''))
        if bt_status in ['待处理', '进行中'] and bt_person not in ['', '-', 'nan', 'None']:
            key = 'BT_pending' if bt_status == '待处理' else 'BT_in_progress'
            person_stats[bt_person][key] += 1

        # TS阶段 — 责任人取 负责人 列（TS无独立负责人字段）
        ts_status = str(row.get('TS状态_标准', ''))
        ts_person = str(row.get('负责人', ''))
        if ts_status in ['待处理', '进行中'] and ts_person not in ['', '-', 'nan', 'None']:
            key = 'TS_pending' if ts_status == '待处理' else 'TS_in_progress'
            person_stats[ts_person][key] += 1

    result = []
    for person, stats in person_stats.items():
        total = sum(stats.values())
        result.append({
            'person': person,
            'FS_pending': stats['FS_pending'],
            'FS_in_progress': stats['FS_in_progress'],
            'BT_pending': stats['BT_pending'],
            'BT_in_progress': stats['BT_in_progress'],
            'TS_pending': stats['TS_pending'],
            'TS_in_progress': stats['TS_in_progress'],
            'total_blocked': total,
        })
    result.sort(key=lambda x: x['total_blocked'], reverse=True)
    return result


# ============================================================
# 必填字段完整度
# ============================================================
def compute_field_completeness(df):
    """必填字段完整度分析"""
    # 排除已取消任务：已取消任务不计入字段完整度各指标
    df = df[df['完成标记'] != '已取消'].copy()

    total = len(df)
    undone_df = df[df['完成标记'] == '未完成']

    # 每行必填字段计数（含系统特有字段，条件字段按状态判定）
    def _required_fields_for_row(row):
        fields = list(REQUIRED_FIELDS)
        syst = str(row.get('系统类型', ''))
        if syst == 'SAP':
            fields += [f for f in SAP_ONLY_FIELDS if f in df.columns]
            # TS已完成时才要求TS实际结束日期、TS文档、TS附件
            ts_status = str(row.get('TS状态_标准', ''))
            if ts_status == '已完成':
                fields += [f for f in SAP_TS_CONDITIONAL_FIELDS if f in df.columns]
        elif syst == 'JAVA-专业系统':
            fields += [f for f in JAVA_ONLY_FIELDS if f in df.columns]
        return fields

    df['_required_count'] = df.apply(lambda row: len(_required_fields_for_row(row)), axis=1)
    df['_filled_count'] = df.apply(lambda row: sum(1 for f in _required_fields_for_row(row) if is_filled(row[f])), axis=1)
    df['_completeness'] = df.apply(lambda row: row['_filled_count'] / row['_required_count'] * 100 if row['_required_count'] > 0 else 0, axis=1)

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
        missing = [f for f in _required_fields_for_row(row) if not is_filled(row[f])]
        if missing:
            undone_field_issues.append({
                'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
                'system': str(row.get('系统类型', '')),
                'task': str(row.get('任务名称', ''))[:60], 'status': str(row.get('状态_标准', '')),
                'person': str(row.get('负责人', '')),
                'missing_count': len(missing), 'missing_fields': ', '.join(missing),
                # 详细信息（供报告点击弹窗展示）
                'task_full': str(row.get('任务名称', '')),
                'type': str(row.get('任务类型', '')), 'priority': str(row.get('优先级', '')),
                'select_type': str(row.get('选择类型', '')), 'desc': str(row.get('描述', '')),
                'progress': str(row.get('进度', '')), 'module': str(row.get('模块', '')),
                'start': str(row.get('开始日期', '')), 'end': str(row.get('结束日期', '')),
                'plan_days': str(row.get('计划开发人天', '')),
                'fs_status': str(row.get('FS状态', '')), 'fs_person': str(row.get('FS负责人', '')),
                'fs_plan_end': str(row.get('FS计划结束日期', '')),
                'bt_status': str(row.get('业务测试状态', '')), 'bt_person': str(row.get('业务测试负责人', '')),
                'bt_plan_start': str(row.get('业务测试计划开始日期', '')),
                'bt_plan_end': str(row.get('业务测试计划结束日期', '')),
                'ts_status': str(row.get('TS状态', '')),
                'ts_plan_end': str(row.get('TS计划结束日期', '')),
                'ts_actual_end': str(row.get('TS实际结束日期', '')),
                'ts_doc': str(row.get('TS文档', '')),
                'ts_attach': str(row.get('TS附件', '')),
                'sys_test': str(row.get('系统测试报告', '')),
                'integ_test': str(row.get('集成测试报告', '')),
                'sys_test_attach': str(row.get('系统测试报告附件', '')),
                'integ_test_attach': str(row.get('集成测试报告附件', '')),
                'delay_reason': str(row.get('延期原因', '')), 'remark': str(row.get('备注', '')),
                'missing_list': missing,
            })
    undone_field_issues.sort(key=lambda x: x['missing_count'], reverse=True)

    # 已完成任务必填字段问题（含条件必填、系统特有字段、阶段流程违规）
    done_df = df[df['完成标记'] == '已完成']

    # 运行质量检查，获取额外违规字段
    from data_quality import check_conditional_required, check_system_specific_fields, check_phase_flow
    from collections import defaultdict
    extra_map = defaultdict(list)  # (project, task[:60]) -> [field_name, ...]
    for v in check_conditional_required(done_df):
        # 从 issue 中提取字段名（如 "FS实际结束日期未填写" → "FS实际结束日期"）
        issue = v.get('issue', '')
        field_name = issue.replace('未填写', '') if '未填写' in issue else v.get('condition', '')
        extra_map[(v['project'], v['task'])].append(field_name)
    for v in check_system_specific_fields(done_df):
        extra_map[(v['project'], v['task'])].append(v.get('field', ''))
    for v in check_phase_flow(done_df):
        extra_map[(v['project'], v['task'])].append(v.get('field', ''))

    done_field_issues = []
    for _, row in done_df.iterrows():
        missing = [f for f in _required_fields_for_row(row) if not is_filled(row[f])]
        task_key = (str(row.get('项目', '')), str(row.get('任务名称', ''))[:60])
        extra_fields = extra_map.get(task_key, [])
        # 合并去重（required_field_missing 可能与 phase_flow 等重复）
        seen = set()
        all_missing = []
        for f in missing + extra_fields:
            if f and f not in seen:
                seen.add(f)
                all_missing.append(f)
        if all_missing:
            done_field_issues.append({
                'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
                'system': str(row.get('系统类型', '')),
                'task': str(row.get('任务名称', ''))[:60], 'status': str(row.get('状态_标准', '')),
                'person': str(row.get('负责人', '')),
                'missing_count': len(all_missing), 'missing_fields': ', '.join(all_missing),
                # 详细信息（供报告点击弹窗展示）
                'task_full': str(row.get('任务名称', '')),
                'type': str(row.get('任务类型', '')), 'priority': str(row.get('优先级', '')),
                'select_type': str(row.get('选择类型', '')), 'desc': str(row.get('描述', '')),
                'progress': str(row.get('进度', '')), 'module': str(row.get('模块', '')),
                'start': str(row.get('开始日期', '')), 'end': str(row.get('结束日期', '')),
                'plan_days': str(row.get('计划开发人天', '')),
                'fs_status': str(row.get('FS状态', '')), 'fs_person': str(row.get('FS负责人', '')),
                'fs_plan_end': str(row.get('FS计划结束日期', '')),
                'fs_actual_end': str(row.get('FS实际结束日期', '')),
                'fs_doc': str(row.get('FS文档', '')), 'fs_attach': str(row.get('FS附件', '')),
                'bt_status': str(row.get('业务测试状态', '')), 'bt_person': str(row.get('业务测试负责人', '')),
                'bt_plan_start': str(row.get('业务测试计划开始日期', '')),
                'bt_plan_end': str(row.get('业务测试计划结束日期', '')),
                'bt_actual_start': str(row.get('业务测试实际开始日期', '')),
                'bt_actual_end': str(row.get('业务测试实际结束日期', '')),
                'ts_status': str(row.get('TS状态', '')),
                'ts_plan_end': str(row.get('TS计划结束日期', '')),
                'ts_actual_end': str(row.get('TS实际结束日期', '')),
                'ts_doc': str(row.get('TS文档', '')), 'ts_attach': str(row.get('TS附件', '')),
                'sys_test': str(row.get('系统测试报告', '')),
                'integ_test': str(row.get('集成测试报告', '')),
                'sys_test_attach': str(row.get('系统测试报告附件', '')),
                'integ_test_attach': str(row.get('集成测试报告附件', '')),
                'delay_reason': str(row.get('延期原因', '')), 'remark': str(row.get('备注', '')),
                'missing_list': all_missing,
            })
    done_field_issues.sort(key=lambda x: x['missing_count'], reverse=True)

    return field_comp_all, batch_system_field_comp, undone_field_issues, done_field_issues


# ============================================================
# 必填字段完整度 — 按项目下钻
# ============================================================
def compute_field_comp_by_project(df):
    """按项目计算必填字段完整度排名"""
    # 排除已取消任务：已取消任务不计入项目字段完整度排名
    df = df[df['完成标记'] != '已取消'].copy()

    total_fields = len(REQUIRED_FIELDS)
    result = []
    for proj in sorted(df['项目'].unique()):
        pdf = df[df['项目'] == proj]
        if len(pdf) == 0:
            continue
        filled = pdf.apply(lambda row: sum(1 for f in REQUIRED_FIELDS if f in df.columns and is_filled(row[f])), axis=1)
        avg_rate = round(filled.sum() / (total_fields * len(pdf)) * 100, 1) if total_fields > 0 else 0
        perfect_count = int(len(pdf[pdf['_completeness'] == 100])) if '_completeness' in pdf.columns else int((filled == total_fields).sum())
        result.append({
            'project': proj,
            'batch': pdf['批次'].iloc[0],
            'system': pdf['系统类型'].iloc[0],
            'total_tasks': len(pdf),
            'avg_rate': avg_rate,
            'perfect': perfect_count,
            'perfect_rate': pct(perfect_count, len(pdf)),
        })
    result.sort(key=lambda x: x['avg_rate'])
    return result


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
    """批次上线时间节点 & 开发截止预警（分母排除已取消）"""
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
        bdone = int(len(bdf[bdf['状态_标准'] == '已完成']))
        bcancelled = int(len(bdf[bdf['状态_标准'] == '已取消']))
        effective_total = len(bdf) - bcancelled
        deadline_analysis.append({
            'batch': batch,
            'go_live': go_live.strftime('%Y/%m/%d'),
            'dev_deadline': dev_dl.strftime('%Y/%m/%d'),
            'days_left': days_to_dl,
            'total': len(bdf),
            'done': bdone, 'cancelled': bcancelled,
            'done_rate': pct(bdone, effective_total),
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
    """已完成任务的验收就绪分析（测试报告 & 业务测试 & 附件）"""
    done_df = df[df['完成标记'] == '已完成']
    acceptance = []
    for _, row in done_df.iterrows():
        # 测试报告检查
        tests = []
        for tc in ['系统测试报告', '集成测试报告', '回归测试报告']:
            if tc in df.columns:
                v = str(row.get(tc, ''))
                tests.append(v not in ['', '-', 'nan', 'None'])
        # 测试报告附件检查
        test_attachments = []
        for ac in ['系统测试报告附件', '集成测试报告附件', '回归测试报告附件']:
            if ac in df.columns:
                v = str(row.get(ac, ''))
                test_attachments.append(is_filled(v))
        bt_status = str(row.get('业务测试状态_标准', ''))
        bt_start = str(row.get('业务测试实际开始日期', ''))
        bt_end = str(row.get('业务测试实际结束日期', ''))
        bt_ok = bt_status in ['已完成'] and is_filled(bt_start) and is_filled(bt_end)
        # FS文档 / FS附件检查
        fs_doc = str(row.get('FS文档', ''))
        fs_attach = str(row.get('FS附件', ''))
        fs_doc_ok = is_filled(fs_doc)
        fs_attach_ok = is_filled(fs_attach)
        # TS文档 / TS附件检查
        ts_doc = str(row.get('TS文档', ''))
        ts_attach = str(row.get('TS附件', ''))
        ts_doc_ok = is_filled(ts_doc)
        ts_attach_ok = is_filled(ts_attach)
        test_count = sum(tests)
        attach_count = sum(test_attachments)
        acceptance.append({
            'project': str(row.get('项目', '')), 'batch': str(row.get('批次', '')),
            'system': str(row.get('系统类型', '')), 'module': str(row.get('模块', '')),
            'task': str(row.get('任务名称', ''))[:60],
            'type': str(row.get('任务类型', '')), 'person': str(row.get('负责人', '')),
            'end_date': str(row.get('结束日期', '')),
            'bt_status': bt_status,
            'bt_start': bt_start if is_filled(bt_start) else '（未填）',
            'bt_end': bt_end if is_filled(bt_end) else '（未填）',
            'sys_test': '✅' if (len(tests) > 0 and tests[0]) else '❌',
            'integ_test': '✅' if (len(tests) > 1 and tests[1]) else '❌',
            'regr_test': '✅' if (len(tests) > 2 and tests[2]) else '❌',
            'sys_test_attach': '✅' if (len(test_attachments) > 0 and test_attachments[0]) else '❌',
            'integ_test_attach': '✅' if (len(test_attachments) > 1 and test_attachments[1]) else '❌',
            'regr_test_attach': '✅' if (len(test_attachments) > 2 and test_attachments[2]) else '❌',
            'fs_doc': '✅' if fs_doc_ok else '❌',
            'fs_attach': '✅' if fs_attach_ok else '❌',
            'ts_doc': '✅' if ts_doc_ok else '❌',
            'ts_attach': '✅' if ts_attach_ok else '❌',
            'test_count': test_count,
            'attach_count': attach_count,
            'all_ready': test_count == 3 and bt_ok and attach_count == 3,
        })

    # 验收汇总（按项目×批次×系统）
    acc_summary = []
    for proj in sorted(df['项目'].unique()):
        pacc = [a for a in acceptance if a['project'] == proj]
        if not pacc:
            continue
        batch = pacc[0]['batch']
        syst = pacc[0]['system']
        fs_doc_total = sum(1 for a in pacc if a.get('fs_doc', '❌') == '✅')
        acc_summary.append({
            'project': proj, 'batch': batch, 'system': syst,
            'total_done': len(pacc),
            'bt_complete': sum(1 for a in pacc if a['bt_status'] == '已完成'),
            'fs_doc_ok': fs_doc_total,
            'fs_doc_rate': pct(fs_doc_total, len(pacc)),
            'fs_attach_ok': sum(1 for a in pacc if a.get('fs_attach', '❌') == '✅'),
            'fs_attach_rate': pct(sum(1 for a in pacc if a.get('fs_attach', '❌') == '✅'), len(pacc)),
            'ts_doc_ok': sum(1 for a in pacc if a.get('ts_doc', '❌') == '✅'),
            'ts_doc_rate': pct(sum(1 for a in pacc if a.get('ts_doc', '❌') == '✅'), len(pacc)),
            'ts_attach_ok': sum(1 for a in pacc if a.get('ts_attach', '❌') == '✅'),
            'ts_attach_rate': pct(sum(1 for a in pacc if a.get('ts_attach', '❌') == '✅'), len(pacc)),
            'sys_test_ok': sum(1 for a in pacc if a['sys_test'] == '✅'),
            'sys_test_rate': pct(sum(1 for a in pacc if a['sys_test'] == '✅'), len(pacc)),
            'integ_test_ok': sum(1 for a in pacc if a['integ_test'] == '✅'),
            'regr_test_ok': sum(1 for a in pacc if a['regr_test'] == '✅'),
            'sys_test_attach_ok': sum(1 for a in pacc if a.get('sys_test_attach', '❌') == '✅'),
            'sys_test_attach_rate': pct(sum(1 for a in pacc if a.get('sys_test_attach', '❌') == '✅'), len(pacc)),
            'integ_test_attach_ok': sum(1 for a in pacc if a.get('integ_test_attach', '❌') == '✅'),
            'regr_test_attach_ok': sum(1 for a in pacc if a.get('regr_test_attach', '❌') == '✅'),
            'all_ready': sum(1 for a in pacc if a['all_ready']),
            'ready_rate': pct(sum(1 for a in pacc if a['all_ready']), len(pacc)),
            'fs_doc_missing_tasks': [{'task': a['task'], 'module': a['module'], 'person': a['person'], 'end_date': a['end_date']} for a in pacc if a.get('fs_doc', '❌') == '❌'],
            'fs_attach_missing_tasks': [{'task': a['task'], 'module': a['module'], 'person': a['person'], 'end_date': a['end_date']} for a in pacc if a.get('fs_attach', '❌') == '❌'],
            'sys_test_missing_tasks': [{'task': a['task'], 'module': a['module'], 'person': a['person'], 'end_date': a['end_date']} for a in pacc if a['sys_test'] == '❌'],
            'sys_test_attach_missing_tasks': [{'task': a['task'], 'module': a['module'], 'person': a['person'], 'end_date': a['end_date']} for a in pacc if a.get('sys_test_attach', '❌') == '❌'],
            'ts_doc_missing_tasks': [{'task': a['task'], 'module': a['module'], 'person': a['person'], 'end_date': a['end_date']} for a in pacc if a.get('ts_doc', '❌') == '❌'],
            'ts_attach_missing_tasks': [{'task': a['task'], 'module': a['module'], 'person': a['person'], 'end_date': a['end_date']} for a in pacc if a.get('ts_attach', '❌') == '❌'],
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
# 执行摘要：自动提取报告中最关键的 3~7 条管理发现
# ============================================================
def compute_executive_summary(proj_ranking, deadline_analysis, overdue_list, near_due_list, acc_summary, kpi):
    """根据已有统计数据自动生成执行摘要，供管理者30秒内掌握全局"""
    items = []

    # 1. 最低完成率项目（完成率 < 50%，最多 3 个）
    low_projs = [p for p in proj_ranking if p['rate'] < 50][:3]
    for p in low_projs:
        items.append({
            'level': 'critical',
            'icon': '🔴',
            'title': f'{p["batch"]} {p["system"]} 「{p["project"]}」完成率仅 {p["rate"]}%，{p["undone"]}/{p["total"]} 未完成',
            'detail': f'逾期 {p["overdue"]} 条，临期 {p["near_due"]} 条，人天 {p["days"]}',
        })

    # 2. 批次截止预警（已超期 / 即将截止）
    for dl in deadline_analysis:
        if dl['past_due']:
            items.append({
                'level': 'critical',
                'icon': '🔴',
                'title': f'{dl["batch"]} 开发截止已超期 {abs(dl["days_left"])} 天，尚有 {dl["over_dev"]} 条任务未在截止前完成',
                'detail': f'整体完成率 {dl["done_rate"]}%，已完成但超截止 {dl["done_late"]} 条',
            })
        elif dl['urgent']:
            items.append({
                'level': 'warning',
                'icon': '🟡',
                'title': f'{dl["batch"]} 开发截止仅剩 {dl["days_left"]} 天，尚有 {dl["over_dev"]} 条任务面临延期风险',
                'detail': f'整体完成率 {dl["done_rate"]}%',
            })

    # 3. 逾期原因填写率（管理流程指标）
    all_risk = overdue_list + near_due_list
    if all_risk:
        reason_filled = sum(1 for x in all_risk if x.get('reason', '（未填写）') not in ['（未填写）', '-', ''])
        reason_rate = round(reason_filled / len(all_risk) * 100, 1)
        if reason_rate < 50:
            items.append({
                'level': 'warning',
                'icon': '🟡',
                'title': f'逾期/临期任务延期原因填写率仅 {reason_rate}%（{reason_filled}/{len(all_risk)}），项目管理流程存在缺口',
                'detail': '建议要求各负责人补充延期原因与备注，否则无法进行归因分析',
            })

    # 4. 逾期任务集中分布
    if overdue_list:
        batch_overdue = Counter(x['batch'] for x in overdue_list)
        if batch_overdue:
            top_batch = batch_overdue.most_common(1)[0]
            pct_val = round(top_batch[1] / len(overdue_list) * 100)
            items.append({
                'level': 'info',
                'icon': 'ℹ️',
                'title': f'逾期任务集中在 {top_batch[0]}（{top_batch[1]} 条），占全部逾期的 {pct_val}%',
                'detail': f'共 {len(overdue_list)} 条逾期，{len(near_due_list)} 条临期',
            })

    # 5. 验收就绪风险（已完成但材料不全的项目，任务数 ≥ 5 且就绪率 < 50%）
    if acc_summary:
        low_ready = [a for a in acc_summary if a['ready_rate'] < 50 and a['total_done'] >= 5][:2]
        for a in low_ready:
            items.append({
                'level': 'warning',
                'icon': '🟡',
                'title': f'{a["project"]} 验收就绪率仅 {a["ready_rate"]}%（{a["all_ready"]}/{a["total_done"]}），材料不全影响验收',
                'detail': f'业务测试完成 {a["bt_complete"]}，系统测试报告 {a["sys_test_ok"]}，集成测试报告 {a["integ_test_ok"]}，回归测试报告 {a["regr_test_ok"]}',
            })

    # 6. 全局完成率低谷提示
    if kpi['comp_rate'] < 70:
        items.append({
            'level': 'warning',
            'icon': '🟡',
            'title': f'全局完成率仅 {kpi["comp_rate"]}%（{kpi["done"]}/{kpi["total"]}），整体进度存在风险',
            'detail': f'未完成 {kpi["undone"]} 条，逾期 {kpi["overdue"]} 条，涉及 {kpi["projects"]} 个项目标段',
        })

    return items[:7]


def compute_system_batch_priority(df):
    """系统类型 × 批次：整体完成进度 + 中高优先级（高+中）完成进度（分母排除已取消）"""
    result = []
    for st in SYSTEM_TYPES:
        for batch in BATCHES:
            sb = df[(df['系统类型'] == st) & (df['批次'] == batch)]
            if len(sb) == 0:
                continue
            # 整体
            total = len(sb)
            done = len(sb[sb['完成标记'] == '已完成'])
            cancelled = len(sb[sb['完成标记'] == '已取消'])
            effective_total = total - cancelled
            # 中高优先级（高 + 中）
            mh = sb[sb['优先级'].isin(['高', '中'])]
            mh_total = len(mh)
            mh_done = len(mh[mh['完成标记'] == '已完成'])
            mh_cancelled = len(mh[mh['完成标记'] == '已取消'])
            mh_effective = mh_total - mh_cancelled
            # 中高优先级剩余未完成任务明细（不含已完成、已取消）
            mh_remaining_df = mh[~mh['完成标记'].isin(['已完成', '已取消'])]
            mh_remaining_tasks = []
            for _, row in mh_remaining_df.iterrows():
                end_dt = row.get('结束日期_dt')
                end_str = end_dt.strftime('%Y/%m/%d') if pd.notna(end_dt) else '-'
                fs_s = row.get('FS状态_标准', '-')
                bt_s = row.get('业务测试状态_标准', '-')
                ts_s = row.get('TS状态_标准', '-')
                mh_remaining_tasks.append({
                    'task': str(row.get('任务名称', '')),
                    'project': str(row.get('项目', '')),
                    'module': str(row.get('模块', '')) if pd.notna(row.get('模块')) else '-',
                    'priority': str(row.get('优先级', '')),
                    'status': str(row.get('状态_标准', '')),
                    'person': str(row.get('负责人', '')) if pd.notna(row.get('负责人')) else '-',
                    'end': end_str,
                    'progress': str(row.get('进度', '')),
                    'fs_status': str(fs_s) if pd.notna(row.get('FS状态_标准')) else '-',
                    'bt_status': str(bt_s) if pd.notna(row.get('业务测试状态_标准')) else '-',
                    'ts_status': str(ts_s) if pd.notna(row.get('TS状态_标准')) else '-',
                    'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因')) else '',
                })
            # 低优先级
            low = sb[sb['优先级'] == '低']
            l_total = len(low)
            l_done = len(low[low['完成标记'] == '已完成'])
            l_cancelled = len(low[low['完成标记'] == '已取消'])
            l_effective = l_total - l_cancelled

            result.append({
                'system': st, 'batch': batch,
                'total': total, 'done': done, 'cancelled': cancelled,
                'comp_rate': pct(done, effective_total),
                'mh_total': mh_total, 'mh_done': mh_done, 'mh_cancelled': mh_cancelled, 'mh_rate': pct(mh_done, mh_effective),
                'mh_remaining': mh_total - mh_done - mh_cancelled,
                'mh_remaining_tasks': mh_remaining_tasks,
                'l_total': l_total, 'l_done': l_done, 'l_cancelled': l_cancelled, 'l_remaining': l_total - l_done - l_cancelled, 'l_rate': pct(l_done, l_effective),
                'days': int(sb['人天数值'].sum()),
            })
    # 排序：SAP 在前、JAVA 在后；每系统内 A→B→C→未标注
    sys_order = {'SAP': 0, 'JAVA-专业系统': 1}
    batch_order = {b: i for i, b in enumerate(BATCHES)}
    result.sort(key=lambda x: (sys_order.get(x['system'], 99), batch_order.get(x['batch'], 99)))
    return result


def compute_batch_project_priority(df, batch_label='A批次'):
    """指定批次：系统类型 × 项目完成进度（含中高优先级，分母排除已取消）"""
    bdf = df[df['批次'] == batch_label]
    if len(bdf) == 0:
        return []
    result = []
    for st in SYSTEM_TYPES:
        st_df = bdf[bdf['系统类型'] == st]
        for proj in sorted(st_df['项目'].unique()):
            sb = st_df[st_df['项目'] == proj]
            # 整体
            total = len(sb)
            done = len(sb[sb['完成标记'] == '已完成'])
            cancelled = len(sb[sb['完成标记'] == '已取消'])
            effective_total = total - cancelled
            # 中高优先级（高 + 中）
            mh = sb[sb['优先级'].isin(['高', '中'])]
            mh_total = len(mh)
            mh_done = len(mh[mh['完成标记'] == '已完成'])
            mh_cancelled = len(mh[mh['完成标记'] == '已取消'])
            mh_effective = mh_total - mh_cancelled
            # 中高进行中（状态=进行中，不含已完成/已取消）
            mh_in_progress_df = mh[mh['状态_标准'] == '进行中']
            mh_in_progress_count = len(mh_in_progress_df)
            mh_in_progress_tasks = []
            for _, row in mh_in_progress_df.iterrows():
                end_dt = row.get('结束日期_dt')
                end_str = end_dt.strftime('%Y/%m/%d') if pd.notna(end_dt) else '-'
                fs_s = row.get('FS状态_标准', '-')
                bt_s = row.get('业务测试状态_标准', '-')
                ts_s = row.get('TS状态_标准', '-')
                mh_in_progress_tasks.append({
                    'task': str(row.get('任务名称', '')),
                    'project': str(row.get('项目', '')),
                    'module': str(row.get('模块', '')) if pd.notna(row.get('模块')) else '-',
                    'priority': str(row.get('优先级', '')),
                    'status': str(row.get('状态_标准', '')),
                    'person': str(row.get('负责人', '')) if pd.notna(row.get('负责人')) else '-',
                    'end': end_str,
                    'progress': str(row.get('进度', '')),
                    'fs_status': str(fs_s) if pd.notna(row.get('FS状态_标准')) else '-',
                    'bt_status': str(bt_s) if pd.notna(row.get('业务测试状态_标准')) else '-',
                    'ts_status': str(ts_s) if pd.notna(row.get('TS状态_标准')) else '-',
                    'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因')) else '',
                })
            mh_remaining_df = mh[~mh['完成标记'].isin(['已完成', '已取消'])]
            mh_remaining_tasks = []
            for _, row in mh_remaining_df.iterrows():
                end_dt = row.get('结束日期_dt')
                end_str = end_dt.strftime('%Y/%m/%d') if pd.notna(end_dt) else '-'
                fs_s = row.get('FS状态_标准', '-')
                bt_s = row.get('业务测试状态_标准', '-')
                ts_s = row.get('TS状态_标准', '-')
                mh_remaining_tasks.append({
                    'task': str(row.get('任务名称', '')),
                    'project': str(row.get('项目', '')),
                    'module': str(row.get('模块', '')) if pd.notna(row.get('模块')) else '-',
                    'priority': str(row.get('优先级', '')),
                    'status': str(row.get('状态_标准', '')),
                    'person': str(row.get('负责人', '')) if pd.notna(row.get('负责人')) else '-',
                    'end': end_str,
                    'progress': str(row.get('进度', '')),
                    'fs_status': str(fs_s) if pd.notna(row.get('FS状态_标准')) else '-',
                    'bt_status': str(bt_s) if pd.notna(row.get('业务测试状态_标准')) else '-',
                    'ts_status': str(ts_s) if pd.notna(row.get('TS状态_标准')) else '-',
                    'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因')) else '',
                })
            # 低优先级
            low = sb[sb['优先级'] == '低']
            l_total = len(low)
            l_done = len(low[low['完成标记'] == '已完成'])
            l_cancelled = len(low[low['完成标记'] == '已取消'])
            l_effective = l_total - l_cancelled

            # 业务测试统计（排除已取消任务）
            bt_base = sb[sb['完成标记'] != '已取消']
            bt_done_count = len(bt_base[bt_base['业务测试状态_标准'] == '已完成'])
            bt_remaining_df = bt_base[bt_base['业务测试状态_标准'] != '已完成']
            bt_remaining_count = len(bt_remaining_df)
            bt_total_effective = len(bt_base)
            bt_remaining_tasks = []
            for _, row in bt_remaining_df.iterrows():
                end_dt = row.get('结束日期_dt')
                end_str = end_dt.strftime('%Y/%m/%d') if pd.notna(end_dt) else '-'
                bt_remaining_tasks.append({
                    'task': str(row.get('任务名称', '')),
                    'project': str(row.get('项目', '')),
                    'module': str(row.get('模块', '')) if pd.notna(row.get('模块')) else '-',
                    'priority': str(row.get('优先级', '')),
                    'status': str(row.get('状态_标准', '')),
                    'person': str(row.get('负责人', '')) if pd.notna(row.get('负责人')) else '-',
                    'end': end_str,
                    'progress': str(row.get('进度', '')),
                    'bt_status': str(row.get('业务测试状态_标准', '-')),
                    'bt_person': str(row.get('业务测试负责人', '')) if pd.notna(row.get('业务测试负责人')) else '-',
                    'reason': str(row.get('延期原因', '')) if pd.notna(row.get('延期原因')) else '',
                })

            result.append({
                'system': st, 'project': proj, 'batch': batch_label,
                'total': total, 'done': done, 'cancelled': cancelled,
                'comp_rate': pct(done, effective_total),
                'mh_total': mh_total, 'mh_done': mh_done, 'mh_cancelled': mh_cancelled, 'mh_rate': pct(mh_done, mh_effective),
                'mh_in_progress': mh_in_progress_count, 'mh_in_progress_tasks': mh_in_progress_tasks,
                'mh_remaining': mh_total - mh_done - mh_cancelled,
                'mh_remaining_tasks': mh_remaining_tasks,
                'l_total': l_total, 'l_done': l_done, 'l_cancelled': l_cancelled, 'l_remaining': l_total - l_done - l_cancelled, 'l_rate': pct(l_done, l_effective),
                'bt_done': bt_done_count, 'bt_remaining': bt_remaining_count, 'bt_total': bt_total_effective,
                'bt_rate': pct(bt_done_count, bt_total_effective),
                'bt_remaining_tasks': bt_remaining_tasks,
                'days': int(sb['人天数值'].sum()),
            })
    # 排序：SAP 在前、JAVA 在后；每系统内按完成率升序（差的在前）
    sys_order = {'SAP': 0, 'JAVA-专业系统': 1}
    result.sort(key=lambda x: (sys_order.get(x['system'], 99), x['comp_rate']))
    return result


# ============================================================
# BPC前端-独立开发批次 专项监控统计
# ============================================================
def compute_bpc_stats(df, report_date):
    """计算 BPC前端-独立开发批次 的专项监控指标。

    按「已完成 → 验收就绪」「未完成 → 推进风险」两个维度分别监控，
    加上共性问题（人天异常、非标准状态、未分配负责人）。
    """
    bpc_df = df[df['批次'] == BPC_BATCH_LABEL]
    if len(bpc_df) == 0:
        return None

    bpc_deadline = pd.Timestamp(BPC_DEADLINE)
    done_df = bpc_df[bpc_df['完成标记'] == '已完成']
    undone_df = bpc_df[bpc_df['完成标记'] == '未完成']
    cancelled_df = bpc_df[bpc_df['完成标记'] == '已取消']

    # ============================================================
    # 进度总览
    # ============================================================
    total = len(bpc_df)
    done = len(done_df)
    cancelled = len(cancelled_df)
    undone = len(undone_df)
    effective_total = total - cancelled
    rate = pct(done, effective_total)
    total_days = int(bpc_df['人天数值'].sum())
    people = int(bpc_df['负责人'].nunique())

    days_to_deadline = (bpc_deadline - pd.Timestamp(report_date)).days
    if days_to_deadline < 0:
        deadline_status, deadline_label = 'past_due', f'已超期 {abs(days_to_deadline)} 天'
    elif days_to_deadline <= 7:
        deadline_status, deadline_label = 'urgent', f'仅剩 {days_to_deadline} 天'
    else:
        deadline_status, deadline_label = 'normal', f'还剩 {days_to_deadline} 天'

    # ============================================================
    # 维度一：已完成任务 → 验收就绪
    # ============================================================
    acceptance_fields = {}
    for f in ['系统测试报告', '集成测试报告', '回归测试报告',
              '系统测试报告附件', '集成测试报告附件', '回归测试报告附件',
              'FS文档', 'FS附件', '业务测试实际开始日期', '业务测试实际结束日期']:
        if f in done_df.columns:
            filled = done_df[f].apply(is_filled).sum()
            acceptance_fields[f] = {'filled': int(filled), 'missing': len(done_df) - int(filled), 'rate': pct(filled, len(done_df))}

    # 验收材料不全明细
    acceptance_issues = []
    report_fields = [f for f in ['系统测试报告', '集成测试报告', '回归测试报告',
                                  '系统测试报告附件', '集成测试报告附件', '回归测试报告附件',
                                  'FS附件'] if f in done_df.columns]
    for _, row in done_df.iterrows():
        missing = [f for f in report_fields if not is_filled(row.get(f, ''))]
        if missing:
            acceptance_issues.append({
                'task': str(row.get('任务名称', ''))[:60],
                'desc': str(row.get('描述', ''))[:80],
                'missing': ', '.join(missing),
                'missing_count': len(missing),
                'person': str(row.get('负责人', '')),
                'bt_status': str(row.get('业务测试状态_标准', '-')),
                'end': str(row.get('结束日期', '-')),
            })
    acceptance_issues.sort(key=lambda x: -x['missing_count'])

    # ============================================================
    # 维度二：未完成任务 → 推进风险
    # ============================================================
    # 2.1 逾期任务
    not_closed = ~undone_df['状态_标准'].isin(['已完成', '已取消'])
    overdue_list = []
    if '结束日期_dt' in undone_df.columns:
        odf = undone_df[not_closed & (undone_df['结束日期_dt'] < report_date)]
        for _, row in odf.iterrows():
            days_overdue = (report_date - row['结束日期_dt']).days
            overdue_list.append(task_row(row, report_date, days_overdue, '逾期'))

    # 2.2 无计划结束日期
    no_end_date = undone_df[~undone_df['结束日期'].apply(is_filled)]
    no_end_list = []
    for _, row in no_end_date.iterrows():
        no_end_list.append({
            'task': str(row.get('任务名称', ''))[:60],
            'desc': str(row.get('描述', ''))[:80],
            'status': str(row.get('状态_标准', '')),
            'person': str(row.get('负责人', '')),
            'progress': str(row.get('进度', '')),
            'fs_status': str(row.get('FS状态_标准', '-')),
        })

    # 2.3 待处理从未启动
    pending_zero = undone_df[(undone_df['状态_标准'] == '待处理') & (undone_df['进度数值'] == 0)]
    pending_zero_list = []
    for _, row in pending_zero.iterrows():
        pending_zero_list.append({
            'task': str(row.get('任务名称', ''))[:60],
            'desc': str(row.get('描述', ''))[:80],
            'person': str(row.get('负责人', '')),
            'fs_status': str(row.get('FS状态_标准', '-')),
        })

    # 2.4 未完成任务的必填字段缺失
    def _req_fields_for_row(row):
        return [f for f in REQUIRED_FIELDS if f in undone_df.columns]

    undone_missing_rows = []
    for _, row in undone_df.iterrows():
        req = _req_fields_for_row(row)
        missing = [f for f in req if not is_filled(row[f])]
        if len(missing) >= 4:
            undone_missing_rows.append({
                'task': str(row.get('任务名称', ''))[:60],
                'missing_count': len(missing),
                'missing_fields': ', '.join(missing[:6]),
                'status': str(row.get('状态_标准', '')),
                'person': str(row.get('负责人', '')),
            })
    undone_missing_rows.sort(key=lambda x: -x['missing_count'])

    # 未完成必填字段整体填写率
    undone_field_comp = {}
    for field in REQUIRED_FIELDS:
        if field not in undone_df.columns:
            continue
        filled = undone_df[field].apply(is_filled).sum()
        undone_field_comp[field] = {
            'filled': int(filled), 'missing': len(undone_df) - int(filled),
            'rate': pct(filled, len(undone_df)),
        }

    # ============================================================
    # 维度三：共性问题
    # ============================================================
    # 人天异常（>= 10 天）
    man_day_anomalies = []
    high_days = bpc_df[bpc_df['人天数值'] >= 10]
    for _, row in high_days.iterrows():
        end_dt = row.get('结束日期_dt')
        end_str = end_dt.strftime('%Y/%m/%d') if pd.notna(end_dt) else '-'
        man_day_anomalies.append({
            'task': str(row.get('任务名称', ''))[:60],
            'desc': str(row.get('描述', ''))[:80],
            'days': row['人天数值'],
            'status': str(row.get('状态_标准', '')),
            'person': str(row.get('负责人', '')),
            'end': end_str,
            'progress': str(row.get('进度', '')),
            'fs_status': str(row.get('FS状态_标准', '-')),
            'done_mark': str(row.get('完成标记', '')),
        })
    man_day_anomalies.sort(key=lambda x: -x['days'])

    # 非标准状态
    normal_statuses = ['已完成', '待处理', '进行中', '已取消']
    abnormal = bpc_df[~bpc_df['状态_标准'].isin(normal_statuses)]
    abnormal_status_list = []
    for _, row in abnormal.iterrows():
        abnormal_status_list.append({
            'task': str(row.get('任务名称', ''))[:60],
            'desc': str(row.get('描述', ''))[:80],
            'status': str(row.get('状态_标准', '')),
            'person': str(row.get('负责人', '')),
            'progress': str(row.get('进度', '')),
            'done_mark': str(row.get('完成标记', '')),
        })

    # 未分配负责人
    unassigned_df = bpc_df[~bpc_df['负责人'].apply(is_filled)]
    unassigned_list = []
    for _, row in unassigned_df.iterrows():
        unassigned_list.append({
            'task': str(row.get('任务名称', ''))[:60],
            'desc': str(row.get('描述', ''))[:80],
            'status': str(row.get('状态_标准', '')),
            'progress': str(row.get('进度', '')),
            'done_mark': str(row.get('完成标记', '')),
        })

    return {
        # 进度总览
        'total': total, 'done': done, 'cancelled': cancelled, 'undone': undone,
        'comp_rate': rate, 'total_days': total_days, 'people': people,
        'deadline': bpc_deadline.strftime('%Y/%m/%d'),
        'days_to_deadline': days_to_deadline,
        'deadline_status': deadline_status, 'deadline_label': deadline_label,
        # 已完成 → 验收就绪
        'acceptance_fields': acceptance_fields,
        'acceptance_issues': acceptance_issues[:50],
        'acceptance_issue_count': len(acceptance_issues),
        # 未完成 → 推进风险
        'overdue': len(overdue_list),
        'overdue_list': overdue_list,
        'no_end_date_count': len(no_end_date),
        'no_end_list': no_end_list[:20],
        'pending_zero_count': len(pending_zero),
        'pending_zero_list': pending_zero_list[:20],
        'undone_missing_rows': undone_missing_rows[:20],
        'undone_field_comp': undone_field_comp,
        'undone_total': len(undone_df),
        # 共性问题
        'man_day_anomalies': man_day_anomalies,
        'man_day_median': round(bpc_df['人天数值'].median(), 1),
        'abnormal_count': len(abnormal),
        'abnormal_status_list': abnormal_status_list,
        'abnormal_status_counter': dict(Counter(str(s) for s in abnormal['状态_标准'].values).most_common()),
        'unassigned_count': len(unassigned_df),
        'unassigned_list': unassigned_list[:50],
    }


# ============================================================
# 总入口：计算所有统计指标
# ============================================================
def compute_all_stats(df, report_date_str='2026/7/22'):
    """计算所有分析统计指标（含数据质量维度），返回字典
    
    通用 PMO 指标排除 BPC独立开发批次，BPC 由专项板块独立监控。
    """
    report_date = pd.Timestamp(report_date_str)

    # 通用 PMO 数据：排除 BPC前端-独立开发批次（已有专项监控）
    non_bpc_df = df[df['项目'] != 'BPC前端-独立开发批次']

    # 逾期 & 临期（开发 + 业务测试）
    overdue_list, near_due_list = compute_risk(non_bpc_df, report_date)
    bt_overdue_list, bt_near_due_list = compute_bt_risk(non_bpc_df, report_date)

    # 数据质量（全量数据，作为原生统计维度）
    from data_quality import compute_quality_dimension
    quality = compute_quality_dimension(df)

    # 各模块统计（排除 BPC）
    proj_ranking = compute_proj_ranking(non_bpc_df, overdue_list, near_due_list)
    kpi = compute_kpi(non_bpc_df, overdue_list, near_due_list)
    batch_kpi = compute_batch_kpi(non_bpc_df, overdue_list, near_due_list)
    system_kpi = compute_system_kpi(non_bpc_df, overdue_list, near_due_list)
    batch_system = compute_batch_system(non_bpc_df)
    sys_batch_priority = compute_system_batch_priority(non_bpc_df)
    a_batch_project_priority = compute_batch_project_priority(non_bpc_df, 'A批次')
    b_batch_project_priority = compute_batch_project_priority(non_bpc_df, 'B批次')
    c_batch_project_priority = compute_batch_project_priority(non_bpc_df, 'C批次')
    team_detail = compute_team_detail(non_bpc_df)
    module_detail = compute_module_detail(non_bpc_df)
    undone_detail = compute_undone_detail(non_bpc_df)
    cancelled_detail = compute_cancelled_detail(non_bpc_df)
    field_comp_all, batch_system_field_comp, undone_field_issues, done_field_issues = compute_field_completeness(non_bpc_df)
    field_comp_by_project = compute_field_comp_by_project(non_bpc_df)
    # 阶段卡点分析
    phase_blockage = compute_phase_blockage(non_bpc_df)
    phase_blockage_by_project = compute_phase_blockage_by_project(non_bpc_df)
    phase_blockage_by_person = compute_phase_blockage_by_person(non_bpc_df)
    monthly_detail = compute_monthly_trend(non_bpc_df)
    deadline_analysis = compute_deadline_analysis(non_bpc_df, report_date)
    acceptance, acc_summary = compute_acceptance(non_bpc_df)
    delayed_detail = enrich_risk_with_reason(non_bpc_df, overdue_list, near_due_list)

    # BPC前端-独立开发批次 专项监控（全量 BPC 数据）
    bpc_stats = compute_bpc_stats(df, report_date)

    # 执行摘要（依赖已完成的多项统计结果）
    executive_summary = compute_executive_summary(
        proj_ranking, deadline_analysis, delayed_detail, near_due_list, acc_summary, kpi)

    return {
        'report_date': report_date_str, 'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'kpi': kpi, 'overdue_list': delayed_detail, 'near_due_list': near_due_list,
        'bt_overdue_list': bt_overdue_list, 'bt_near_due_list': bt_near_due_list,
        'proj_ranking': proj_ranking,
        'batch_kpi': batch_kpi, 'system_kpi': system_kpi, 'batch_system': batch_system,
        'sys_batch_priority': sys_batch_priority,
        'a_batch_project_priority': a_batch_project_priority,
        'b_batch_project_priority': b_batch_project_priority,
        'c_batch_project_priority': c_batch_project_priority,
        'team_detail': team_detail, 'module_detail': module_detail,
        'undone_detail': undone_detail, 'cancelled_detail': cancelled_detail,
        'phase_blockage': phase_blockage, 'phase_blockage_by_project': phase_blockage_by_project,
        'phase_blockage_by_person': phase_blockage_by_person,
        'field_comp_all': field_comp_all, 'batch_system_field_comp': batch_system_field_comp,
        'undone_field_issues': undone_field_issues, 'done_field_issues': done_field_issues, 'field_comp_by_project': field_comp_by_project,
        'monthly_detail': monthly_detail,
        'deadline_analysis': deadline_analysis,
        'acceptance': acceptance, 'acc_summary': acc_summary,
        'quality': quality,  # 数据质量作为原生统计维度
        'executive_summary': executive_summary,  # 执行摘要
        'bpc_stats': bpc_stats,  # BPC前端-独立开发批次 专项监控
        'batches': BATCHES, 'REQUIRED_FIELDS': REQUIRED_FIELDS, 'required_count': len(REQUIRED_FIELDS),
    }
