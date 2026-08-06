"""PMO 项目监控分析 — 数据质量检查（字段完整度 + 模板规范校验）"""

import pandas as pd
from config import (
    REQUIRED_FIELDS, CONDITIONAL_FIELDS, SAP_ONLY_FIELDS, JAVA_ONLY_FIELDS,
    SAP_TS_CONDITIONAL_FIELDS,
    OPTIONAL_FIELDS, FORBIDDEN_PLACEHOLDERS, STATUS_PROGRESS_RULE,
    MAX_TASK_CYCLE_DAYS, REGRESSION_FIELDS, get_fields_for_system,
)
from data_loader import is_filled, pct


def check_placeholder_violations(df):
    """检查禁止占位符（N/A、null、None等）及必填字段中的'-'违规"""
    violations = []
    check_fields = REQUIRED_FIELDS + list(CONDITIONAL_FIELDS) + list(SAP_ONLY_FIELDS) + list(JAVA_ONLY_FIELDS)
    for _, row in df.iterrows():
        for field in check_fields:
            if field not in df.columns:
                continue
            val = str(row.get(field, ''))
            # 检查禁用占位符（N/A, null, None等）
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
            # 必填字段中'-'也视为占位符违规
            if field in REQUIRED_FIELDS and val.strip() == '-':
                violations.append({
                    'project': str(row.get('项目', '')),
                    'batch': str(row.get('批次', '')),
                    'system': str(row.get('系统类型', '')),
                    'task': str(row.get('任务名称', ''))[:60],
                    'status': str(row.get('状态_标准', '')),
                    'field': field,
                    'value': val,
                    'issue': f'占位符"{val}"（必填字段不得使用"-"占位）',
                })
    return violations


def check_status_progress_linkage(df):
    """检查状态-进度联动规则（已完成/已取消→100%，待处理/未开始→0%，进行中→不得为0%）"""
    violations = []
    for _, row in df.iterrows():
        status = str(row.get('状态_标准', ''))
        progress = row.get('进度数值', 0)
        progress_str = str(row.get('进度', ''))
        # 固定阈值：已完成/已取消→100%，待处理/未开始→0%
        if status in STATUS_PROGRESS_RULE:
            expected = STATUS_PROGRESS_RULE[status]
            if abs(progress - expected) > 0.001:
                violations.append({
                    'project': str(row.get('项目', '')),
                    'batch': str(row.get('批次', '')),
                    'system': str(row.get('系统类型', '')),
                    'task': str(row.get('任务名称', ''))[:60],
                    'status': status,
                    'progress': progress_str,
                    'expected': f'{int(expected * 100)}%',
                    'issue': f'状态="{status}"但进度为{progress_str}，期望{int(expected * 100)}%',
                })
        # 进行中任务进度不应为0%（有状态但无进展）
        elif status == '进行中' and progress == 0:
            violations.append({
                'project': str(row.get('项目', '')),
                'batch': str(row.get('批次', '')),
                'system': str(row.get('系统类型', '')),
                'task': str(row.get('任务名称', ''))[:60],
                'status': status,
                'progress': progress_str,
                'expected': '>0%',
                'issue': f'状态="进行中"但进度为{progress_str}，应有实际进展',
            })
    return violations


def check_date_format(df):
    """检查日期格式（YYYY/MM/DD）及日期逻辑（开始≤结束、阶段顺序）"""
    violations = []
    date_cols = ['开始日期', '结束日期', 'FS计划结束日期', 'FS实际结束日期',
                 '业务测试计划开始日期', '业务测试计划结束日期',
                 '业务测试实际开始日期', '业务测试实际结束日期',
                 'TS计划结束日期', 'TS实际结束日期']

    def _make(row, issue_text, field='', value=''):
        return {
            'project': str(row.get('项目', '')),
            'batch': str(row.get('批次', '')),
            'system': str(row.get('系统类型', '')),
            'task': str(row.get('任务名称', ''))[:60],
            'field': field,
            'value': value,
            'issue': issue_text,
        }

    def _parse_date(val):
        """尝试解析日期，返回 (ok, datetime)"""
        from datetime import datetime
        if pd.isna(val):
            return False, None
        s = str(val).strip()
        if s in ['', '-', 'nan']:
            return False, None
        try:
            return True, datetime.strptime(s, '%Y/%m/%d')
        except ValueError:
            return False, None

    # --- 格式检查（列遍历）---
    for col in date_cols:
        if col not in df.columns:
            continue
        for idx, val in df[col].items():
            if pd.isna(val):
                continue
            s = str(val).strip()
            if s in ['', '-', 'nan']:
                continue
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

    # --- 日期逻辑检查（行遍历）---
    for _, row in df.iterrows():
        # 开始日期 > 结束日期
        ok_start, start_dt = _parse_date(row.get('开始日期'))
        ok_end, end_dt = _parse_date(row.get('结束日期'))
        if ok_start and ok_end and start_dt > end_dt:
            violations.append(_make(row,
                f'开始日期({row.get("开始日期")}) > 结束日期({row.get("结束日期")})',
                '开始日期/结束日期'))

        # FS计划结束日期 > 开始日期（FS应在开发开始前完成）
        ok_fs, fs_dt = _parse_date(row.get('FS计划结束日期'))
        if ok_start and ok_fs and fs_dt > start_dt:
            violations.append(_make(row,
                f'FS计划结束日期({row.get("FS计划结束日期")}) > 开始日期({row.get("开始日期")})，FS应在开发前完成',
                'FS计划结束日期'))

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
        # FS已完成 → FS实际结束日期、FS文档、FS附件必须填写
        fs_status = str(row.get('FS状态_标准', ''))
        if fs_status == '已完成':
            for f in ['FS实际结束日期', 'FS文档', 'FS附件']:
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

        # SAP 特有字段：TS计划结束日期（无条件必填）+ TS已完成时必填字段
        if syst == 'SAP':
            # TS状态不能为'不涉及'
            ts_status = str(row.get('TS状态_标准', ''))
            if ts_status == '不涉及':
                violations.append({
                    'project': str(row.get('项目', '')),
                    'batch': str(row.get('批次', '')),
                    'system': syst,
                    'task': str(row.get('任务名称', ''))[:60],
                    'field': 'TS状态',
                    'issue': 'SAP系统 - TS状态不能为"不涉及"',
                })
            # 无条件必填
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
            # TS已完成时才必填
            if ts_status == '已完成':
                for f in SAP_TS_CONDITIONAL_FIELDS:
                    if f in df.columns and not is_filled(row.get(f, '')):
                        violations.append({
                            'project': str(row.get('项目', '')),
                            'batch': str(row.get('批次', '')),
                            'system': syst,
                            'task': str(row.get('任务名称', ''))[:60],
                            'field': f,
                            'issue': f'SAP系统 - TS已完成，{f}必填',
                        })

        # JAVA 特有字段（当前无必填项，预留扩展）
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


def check_required_field_missing(df):
    """检查 ★必填字段 是否为空（18个必填字段逐一检查）"""
    violations = []
    for _, row in df.iterrows():
        for f in REQUIRED_FIELDS:
            if f not in df.columns:
                continue
            if not is_filled(row.get(f, '')):
                violations.append({
                    'project': str(row.get('项目', '')),
                    'batch': str(row.get('批次', '')),
                    'system': str(row.get('系统类型', '')),
                    'task': str(row.get('任务名称', ''))[:60],
                    'field': f,
                    'status': str(row.get('状态_标准', '')),
                    'issue': f'必填字段「{f}」未填写',
                })
    return violations


def check_phase_flow(df):
    """检查阶段流程逻辑：FS→业务测试→TS 的衔接是否合理"""
    violations = []
    for _, row in df.iterrows():
        fs_status = str(row.get('FS状态_标准', ''))
        bt_status = str(row.get('业务测试状态_标准', ''))
        syst = str(row.get('系统类型', ''))

        # FS已完成 → 业务测试状态不应为空（应已进入下一阶段）
        if fs_status == '已完成' and not is_filled(row.get('业务测试状态', '')):
            violations.append({
                'project': str(row.get('项目', '')),
                'batch': str(row.get('批次', '')),
                'system': syst,
                'task': str(row.get('任务名称', ''))[:60],
                'field': '业务测试状态',
                'issue': 'FS已完成但业务测试状态为空，应更新阶段状态',
            })

        # 业务测试已完成(SAP) → TS状态不应为空
        if bt_status == '已完成' and syst == 'SAP' and not is_filled(row.get('TS状态', '')):
            violations.append({
                'project': str(row.get('项目', '')),
                'batch': str(row.get('批次', '')),
                'system': syst,
                'task': str(row.get('任务名称', ''))[:60],
                'field': 'TS状态',
                'issue': '业务测试已完成(SAP)但TS状态为空，应更新阶段状态',
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
        'phase_flow_issues': check_phase_flow(df),
        'system_field_missing': check_system_specific_fields(df),
        'required_field_missing': check_required_field_missing(df),
    }

    # 汇总
    summary = {}
    for name, items in checks.items():
        summary[name] = {
            'count': len(items),
            'items': items,
            'is_ok': len(items) == 0,
        }

    return summary


# ============================================================
# 多维度质量统计（供报告渲染使用）
# ============================================================
from collections import Counter, defaultdict


def compute_quality_dimension(df):
    """计算数据质量的多维度统计，返回供 HTML 报告渲染的完整数据结构"""
    # 排除已取消任务：已取消任务不计入数据质量各指标
    df = df[df['完成标记'] != '已取消'].copy()

    ALL_CHECKS = [
        'placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
        'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues',
        'system_field_missing', 'required_field_missing',
    ]
    # 1. 执行所有检查
    checks = {
        'placeholder_violations': check_placeholder_violations(df),
        'status_progress_mismatch': check_status_progress_linkage(df),
        'date_format_issues': check_date_format(df),
        'task_cycle_exceeded': check_task_cycle(df),
        'conditional_missing': check_conditional_required(df),
        'phase_flow_issues': check_phase_flow(df),
        'system_field_missing': check_system_specific_fields(df),
        'required_field_missing': check_required_field_missing(df),
    }

    # 1b. 必填字段按字段汇总（供报告展开用）
    total_tasks = len(df)
    req_field_counts = Counter()
    req_field_proj = defaultdict(lambda: defaultdict(int))  # field -> project -> count
    for v in checks['required_field_missing']:
        f = v.get('field', '')
        req_field_counts[f] += 1
        req_field_proj[f][v.get('project', '')] += 1
    required_field_summary = []
    for f, c in req_field_counts.most_common():
        proj_list = req_field_proj[f]
        top_projects = [{'project': p, 'count': pc} for p, pc in sorted(proj_list.items(), key=lambda x: -x[1])]
        required_field_summary.append({
            'field': f,
            'count': c,
            'num_projects': len(proj_list),
            'missing_rate': round(c / total_tasks * 100, 1) if total_tasks > 0 else 0,
            'top_projects': top_projects,
        })

    # 2. 汇总每个检查项
    summary = {}
    total_issues = 0
    for name, items in checks.items():
        summary[name] = {
            'count': len(items),
            'items': items,
            'is_ok': len(items) == 0,
        }
        total_issues += len(items)

    # 3. 合并所有违规记录为扁平列表
    all_violations = []
    for check_name, items in checks.items():
        for item in items:
            item_copy = dict(item)
            item_copy['_check'] = check_name
            all_violations.append(item_copy)

    # 4. 按项目维度聚合
    proj_counter = Counter()
    proj_detail = defaultdict(lambda: defaultdict(int))
    for v in all_violations:
        proj_counter[v['project']] += 1
        proj_detail[v['project']][v['_check']] += 1

    by_project = []
    for proj, total in proj_counter.most_common():
        entry = {'project': proj, 'total': total}
        for ck in ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                     'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing']:
            entry[ck] = proj_detail[proj].get(ck, 0)
        by_project.append(entry)

    # 5. 按批次维度聚合
    batch_counter = Counter()
    batch_detail = defaultdict(lambda: defaultdict(int))
    for v in all_violations:
        batch_counter[v['batch']] += 1
        batch_detail[v['batch']][v['_check']] += 1

    by_batch = []
    for batch_label, total in batch_counter.most_common():
        entry = {'batch': batch_label, 'total': total}
        for ck in ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                     'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing']:
            entry[ck] = batch_detail[batch_label].get(ck, 0)
        by_batch.append(entry)

    # 6. 按系统类型维度聚合
    sys_counter = Counter()
    sys_detail = defaultdict(lambda: defaultdict(int))
    for v in all_violations:
        sys_counter[v['system']] += 1
        sys_detail[v['system']][v['_check']] += 1

    by_system = []
    for syst, total in sys_counter.most_common():
        entry = {'system': syst, 'total': total}
        for ck in ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                     'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing']:
            entry[ck] = sys_detail[syst].get(ck, 0)
        by_system.append(entry)

    # 7. 按任务状态维度聚合（仅状态-进度联动检查有此字段）
    status_items = checks['status_progress_mismatch']
    status_counter = Counter(v.get('status', '') for v in status_items)
    by_status = [{'status': s, 'count': c} for s, c in status_counter.most_common()]

    # 8. 问题最多的Top任务
    task_counter = Counter()
    task_samples = {}
    for v in all_violations:
        key = (v['project'], v['task'])
        task_counter[key] += 1
        if key not in task_samples:
            task_samples[key] = v

    top_tasks = []
    for (proj, task_name), count in task_counter.most_common(30):
        sample = task_samples[(proj, task_name)]
        top_tasks.append({
            'project': proj,
            'batch': sample.get('batch', ''),
            'system': sample.get('system', ''),
            'task': task_name,
            'issues': count,
            'issue_list': [ck for ck in [
                'placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing'
            ] if proj_detail.get(proj, {}).get(ck, 0) > 0],
        })

    # 9. 批次×系统类型 交叉聚合
    batch_sys_counter = Counter()
    batch_sys_detail = defaultdict(lambda: defaultdict(int))
    for v in all_violations:
        key = (v['batch'], v['system'])
        batch_sys_counter[key] += 1
        batch_sys_detail[key][v['_check']] += 1

    by_batch_system = []
    for (batch_label, syst), total in batch_sys_counter.most_common():
        entry = {'batch': batch_label, 'system': syst, 'total': total}
        for ck in ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                     'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing']:
            entry[ck] = batch_sys_detail[(batch_label, syst)].get(ck, 0)
        by_batch_system.append(entry)

    # 10. 构建 (项目, 任务) → (团队, 模块) 查找表（用于团队/模块维度聚合）
    task_meta = {}
    for _, row in df.iterrows():
        proj = str(row.get('项目', ''))
        task_name = str(row.get('任务名称', ''))[:60]
        team = str(row.get('供应商团队', '')) if '供应商团队' in df.columns else str(row.get('项目', ''))[:20]
        module = str(row.get('模块', ''))
        task_meta[(proj, task_name)] = {'team': team, 'module': module}

    # 11. 按团队×批次×系统 维度聚合
    team_counter = Counter()
    team_detail = defaultdict(lambda: defaultdict(int))
    for v in all_violations:
        meta = task_meta.get((v['project'], v['task']), {})
        team = meta.get('team', '未知')
        key = (team, v['batch'], v['system'])
        team_counter[key] += 1
        team_detail[key][v['_check']] += 1

    by_team = []
    for (team, batch_label, syst), total in team_counter.most_common():
        entry = {'team': team, 'batch': batch_label, 'system': syst, 'total': total}
        for ck in ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                     'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing']:
            entry[ck] = team_detail[(team, batch_label, syst)].get(ck, 0)
        by_team.append(entry)

    # 12. 按模块×批次×系统 维度聚合
    module_counter = Counter()
    module_detail = defaultdict(lambda: defaultdict(int))
    for v in all_violations:
        meta = task_meta.get((v['project'], v['task']), {})
        module = meta.get('module', '未知')
        key = (module, v['batch'], v['system'])
        module_counter[key] += 1
        module_detail[key][v['_check']] += 1

    by_module = []
    for (module, batch_label, syst), total in module_counter.most_common():
        entry = {'module': module, 'batch': batch_label, 'system': syst, 'total': total}
        for ck in ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                     'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing']:
            entry[ck] = module_detail[(module, batch_label, syst)].get(ck, 0)
        by_module.append(entry)

    return {
        'summary': summary,
        'total_issues': total_issues,
        'by_project': by_project,
        'by_batch': by_batch,
        'by_system': by_system,
        'by_status': by_status,
        'by_batch_system': by_batch_system,
        'by_team': by_team,
        'by_module': by_module,
        'top_tasks': top_tasks,
        'check_names': ['placeholder_violations', 'status_progress_mismatch', 'date_format_issues',
                        'task_cycle_exceeded', 'conditional_missing', 'phase_flow_issues', 'system_field_missing', 'required_field_missing'],
        'required_field_summary': required_field_summary,
    }
