"""PMO 项目监控分析 — 数据质量检查（字段完整度 + 模板规范校验）"""

import pandas as pd
from config import (
    REQUIRED_FIELDS, CONDITIONAL_FIELDS, SAP_ONLY_FIELDS, JAVA_ONLY_FIELDS,
    OPTIONAL_FIELDS, FORBIDDEN_PLACEHOLDERS, STATUS_PROGRESS_RULE,
    MAX_TASK_CYCLE_DAYS, get_fields_for_system,
)
from data_loader import is_filled, pct


def check_placeholder_violations(df):
    """检查禁止占位符（-、N/A等）违规"""
    violations = []
    check_fields = REQUIRED_FIELDS + list(CONDITIONAL_FIELDS) + list(SAP_ONLY_FIELDS) + list(JAVA_ONLY_FIELDS)
    for _, row in df.iterrows():
        for field in check_fields:
            if field not in df.columns:
                continue
            val = str(row.get(field, ''))
            for ph in FORBIDDEN_PLACEHOLDERS:
                if val.strip().upper() == ph.upper():
                    violations.append({
                        'project': str(row.get('项目', '')),
                        'batch': str(row.get('批次', '')),
                        'system': str(row.get('系统类型', '')),
                        'task': str(row.get('任务名称', ''))[:60],
                        'status': str(row.get('状态_标准', '')),
                        'field': field,
                        'value': val,
                        'issue': f'占位符"{val}"',
                    })
                    break
    return violations


def check_status_progress_linkage(df):
    """检查状态-进度联动规则（已完成→100%，待处理→0%）"""
    violations = []
    for _, row in df.iterrows():
        status = str(row.get('状态_标准', ''))
        if status not in STATUS_PROGRESS_RULE:
            continue
        expected = STATUS_PROGRESS_RULE[status]
        progress = row.get('进度数值', 0)
        if abs(progress - expected) > 0.001:
            violations.append({
                'project': str(row.get('项目', '')),
                'batch': str(row.get('批次', '')),
                'system': str(row.get('系统类型', '')),
                'task': str(row.get('任务名称', ''))[:60],
                'status': status,
                'progress': str(row.get('进度', '')),
                'expected': f'{int(expected * 100)}%',
                'issue': f'状态="{status}"但进度为{row.get("进度", "")}，期望{int(expected * 100)}%',
            })
    return violations


def check_date_format(df):
    """检查日期格式是否统一为 YYYY/MM/DD"""
    violations = []
    date_cols = ['开始日期', '结束日期', 'FS计划结束日期', 'FS实际结束日期',
                 '业务测试计划开始日期', '业务测试计划结束日期',
                 '业务测试实际开始日期', '业务测试实际结束日期',
                 'TS计划结束日期', 'TS实际结束日期']
    for col in date_cols:
        if col not in df.columns:
            continue
        for idx, val in df[col].items():
            if pd.isna(val):
                continue
            s = str(val).strip()
            if s in ['', '-', 'nan']:
                continue
            # 检查是否为 YYYY/MM/DD 格式
            parts = s.split('/')
            if len(parts) != 3 or len(parts[0]) != 4:
                violations.append({
                    'project': str(df.at[idx, '项目']),
                    'batch': str(df.at[idx, '批次']),
                    'system': str(df.at[idx, '系统类型']),
                    'task': str(df.at[idx, '任务名称'])[:60],
                    'field': col,
                    'value': s,
                    'issue': f'日期格式异常: "{s}"，应为 YYYY/MM/DD',
                })
    return violations


def check_task_cycle(df):
    """检查单任务周期是否超过10工作日"""
    violations = []
    if '任务周期' not in df.columns:
        return violations
    for _, row in df.iterrows():
        cycle = row.get('任务周期', 0)
        if pd.notna(cycle) and cycle > MAX_TASK_CYCLE_DAYS:
            violations.append({
                'project': str(row.get('项目', '')),
                'batch': str(row.get('批次', '')),
                'system': str(row.get('系统类型', '')),
                'task': str(row.get('任务名称', ''))[:60],
                'start': str(row.get('开始日期', '')),
                'end': str(row.get('结束日期', '')),
                'cycle_days': int(cycle),
                'issue': f'任务周期 {int(cycle)} 天，超过 {MAX_TASK_CYCLE_DAYS} 工作日上限',
            })
    return violations


def check_conditional_required(df):
    """检查有条件必填字段（#必须）"""
    violations = []
    for _, row in df.iterrows():
        # FS已完成 → FS实际结束日期和FS文档必须填写
        fs_status = str(row.get('FS状态_标准', ''))
        if fs_status == '已完成':
            for f in ['FS实际结束日期', 'FS文档']:
                if f in df.columns and not is_filled(row.get(f, '')):
                    violations.append({
                        'project': str(row.get('项目', '')),
                        'batch': str(row.get('批次', '')),
                        'system': str(row.get('系统类型', '')),
                        'task': str(row.get('任务名称', ''))[:60],
                        'condition': f'FS状态=已完成 → {f}必填',
                        'issue': f'{f}未填写',
                    })
        # 业务测试已完成 → 业务测试实际开始/结束日期必填
        bt_status = str(row.get('业务测试状态_标准', ''))
        if bt_status == '已完成':
            for f in ['业务测试实际开始日期', '业务测试实际结束日期']:
                if f in df.columns and not is_filled(row.get(f, '')):
                    violations.append({
                        'project': str(row.get('项目', '')),
                        'batch': str(row.get('批次', '')),
                        'system': str(row.get('系统类型', '')),
                        'task': str(row.get('任务名称', ''))[:60],
                        'condition': f'业务测试状态=已完成 → {f}必填',
                        'issue': f'{f}未填写',
                    })
    return violations


def check_system_specific_fields(df):
    """检查系统特有字段（●SAP、●JAVA）"""
    violations = []
    for _, row in df.iterrows():
        syst = str(row.get('系统类型', ''))

        # SAP 特有字段：TS计划结束日期、TS实际结束日期、TS文档
        if syst == 'SAP':
            for f in SAP_ONLY_FIELDS:
                if f in df.columns and not is_filled(row.get(f, '')):
                    violations.append({
                        'project': str(row.get('项目', '')),
                        'batch': str(row.get('批次', '')),
                        'system': syst,
                        'task': str(row.get('任务名称', ''))[:60],
                        'field': f,
                        'issue': f'SAP系统 - {f}未填写',
                    })

        # JAVA 特有字段：系统测试报告、集成测试报告、回归测试报告
        if syst == 'JAVA-专业系统':
            for f in JAVA_ONLY_FIELDS:
                if f in df.columns and not is_filled(row.get(f, '')):
                    violations.append({
                        'project': str(row.get('项目', '')),
                        'batch': str(row.get('批次', '')),
                        'system': syst,
                        'task': str(row.get('任务名称', ''))[:60],
                        'field': f,
                        'issue': f'JAVA-专业系统 - {f}未填写',
                    })
    return violations


def run_all_quality_checks(df):
    """运行所有数据质量检查，返回汇总报告"""
    checks = {
        'placeholder_violations': check_placeholder_violations(df),
        'status_progress_mismatch': check_status_progress_linkage(df),
        'date_format_issues': check_date_format(df),
        'task_cycle_exceeded': check_task_cycle(df),
        'conditional_missing': check_conditional_required(df),
        'system_field_missing': check_system_specific_fields(df),
    }

    # 汇总
    summary = {}
    for name, items in checks.items():
        summary[name] = {
            'count': len(items),
            'items': items[:100] if len(items) > 100 else items,
            'is_ok': len(items) == 0,
        }

    return summary
