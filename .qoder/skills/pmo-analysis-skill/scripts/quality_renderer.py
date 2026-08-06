"""PMO 数据质量专项报告 — 独立 HTML 渲染

整合三类质量内容：
  一、填写规范违规（8 类检查 + 规则说明 + 违规样例 + 维度下钻）
  二、必填字段完整度（字段级 / 批次×系统级 / 未完成任务 Top50）
  三、验收就绪分析（项目就绪汇总 + 材料不全明细）
"""

import json
import os


# ============================================================
# CSS（复用主报告样式，确保视觉一致）
# ============================================================
CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;background:#f0f2f5;color:#333;line-height:1.6}
.header{background:linear-gradient(135deg,#4a1d6e 0%,#7c3aed 100%);color:#fff;padding:30px 40px}
.header h1{font-size:28px;margin-bottom:5px}
.header .sub{font-size:14px;opacity:.85}
.header .back-link{display:inline-block;margin-top:10px;color:#ddd;font-size:13px;text-decoration:none;border:1px solid #8860d0;padding:4px 12px;border-radius:6px}
.header .back-link:hover{background:#8860d0;color:#fff}
.container{max-width:1500px;margin:0 auto;padding:20px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}
.kpi-card{background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.08);text-align:center}
.kpi-card .label{font-size:13px;color:#666;margin-bottom:5px}
.kpi-card .value{font-size:30px;font-weight:700}
.kpi-card.green .value{color:#16a34a}
.kpi-card.blue .value{color:#2563eb}
.kpi-card.orange .value{color:#d97706}
.kpi-card.red .value{color:#dc2626}
.kpi-card.purple .value{color:#7c3aed}
.section{background:#fff;border-radius:12px;padding:25px;margin:20px 0;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.section h2{font-size:20px;color:#4a1d6e;border-left:4px solid #7c3aed;padding-left:12px;margin-bottom:20px}
.section h3{font-size:16px;color:#374151;margin:20px 0 12px}
.table-wrap{overflow-x:auto;max-height:600px;overflow-y:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#4a1d6e;color:#fff;padding:8px 6px;text-align:center;font-weight:600;white-space:nowrap;position:sticky;top:0;z-index:1}
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
.alert-success{background:#dcfce7;border:1px solid #86efac;color:#166534}
.footer{text-align:center;padding:20px;color:#9ca3af;font-size:12px}
.clickable-badge{cursor:pointer;text-decoration:underline dotted;transition:transform .1s}
.clickable-badge:hover{transform:scale(1.15);box-shadow:0 1px 4px rgba(0,0,0,.2)}
.modal-mask{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:100;justify-content:center;align-items:center}
.modal-mask.show{display:flex}
.modal-box{background:#fff;border-radius:12px;max-width:780px;width:92%;max-height:85vh;overflow-y:auto;padding:24px;box-shadow:0 10px 40px rgba(0,0,0,.25);position:relative}
.modal-box h3{font-size:16px;color:#4a1d6e;margin-bottom:14px;padding-right:36px;line-height:1.5}
.modal-close{position:absolute;top:14px;right:16px;border:none;background:#f3f4f6;color:#6b7280;width:28px;height:28px;border-radius:50%;font-size:16px;cursor:pointer;line-height:1}
.modal-close:hover{background:#e5e7eb;color:#111}
.fs-diff-link{color:#dc2626;font-weight:600;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.fs-diff-link:hover{color:#b91c1c}
.detail-grid{display:grid;grid-template-columns:150px 1fr 150px 1fr;gap:6px 10px;font-size:13px;margin-bottom:14px}
.detail-grid .k{color:#6b7280;text-align:right;font-weight:600;white-space:nowrap}
.detail-grid .v{color:#111827;text-align:left;word-break:break-all}
.detail-grid .k.miss{color:#dc2626}
.detail-grid .v.miss{color:#dc2626;font-weight:700;background:#fee2e2;border-radius:4px;padding:0 6px;align-self:start;justify-self:start}
@media(max-width:768px){.chart-row{grid-template-columns:1fr}.detail-grid{grid-template-columns:150px 1fr}}
"""
# ============================================================
# 辅助渲染函数
# ============================================================
def _acc_rate_badge(rate):
    """Return CSS class for a readiness rate."""
    return 'badge-green' if rate >= 80 else ('badge-yellow' if rate >= 50 else 'badge-red')

def _render_acc_subtotal(P, rows, label, is_grand=False):
    """Compute and append a subtotal/grand-total row for acceptance matrix."""
    if not rows:
        return
    td = sum(r['total_done'] for r in rows)
    bc = sum(r['bt_complete'] for r in rows)
    fd = sum(r.get('fs_doc_ok', 0) for r in rows)
    fd_diff = td - fd
    fa = sum(r.get('fs_attach_ok', 0) for r in rows)
    fa_diff = td - fa
    st = sum(r['sys_test_ok'] for r in rows)
    sa = sum(r.get('sys_test_attach_ok', 0) for r in rows)
    td_ = sum(r.get('ts_doc_ok', 0) for r in rows)
    ta = sum(r.get('ts_attach_ok', 0) for r in rows)
    ar = sum(r['all_ready'] for r in rows)
    rr = round(ar / td * 100, 1) if td > 0 else 0
    rc = _acc_rate_badge(rr)
    border_style = 'border-top:3px double #7c3aed' if is_grand else 'border-top:1px dashed #c4b5fd'
    bg = '#f5f0ff' if is_grand else '#f8fafc'
    w = '700' if is_grand else '600'
    fd_diff_val = f'<span style="color:#dc2626;font-weight:{w}">{fd_diff}</span>' if fd_diff > 0 else f'<strong>{fd_diff}</strong>'
    fa_diff_val = f'<span style="color:#dc2626;font-weight:{w}">{fa_diff}</span>' if fa_diff > 0 else f'<strong>{fa_diff}</strong>'
    P.append(f'<tr style="font-weight:{w};background:{bg};{border_style}"><td><strong>{label}</strong></td><td>-</td><td><strong>{td}</strong></td><td><strong>{bc}</strong></td><td><strong>{fd}</strong></td><td>{fd_diff_val}</td><td><strong>{fa}</strong></td><td>{fa_diff_val}</td><td><strong>{st}</strong></td><td><strong>{sa}</strong></td><td><strong>{td_}</strong></td><td><strong>{ta}</strong></td></tr>')

def _render_acc_matrix(P, rows, title):
    """Render acceptance readiness matrix: system type x project, with subtotals."""
    if not rows:
        P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">{title}（0条数据）</summary></details>')
        return
    P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">{title}（共 {len(rows)} 个项目）</summary>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>系统类型</th><th>项目</th><th>已完成</th><th>业务测试完成</th><th>FS文档</th><th>FS文档差异</th><th>FS附件</th><th>FS附件差异</th><th>系统测试报告</th><th>系统测试报告附件</th><th>TS文档</th><th>TS附件</th></tr>')
    sap_rows = [r for r in rows if r['system'] == 'SAP']
    java_rows = [r for r in rows if r['system'] == 'JAVA-专业系统']
    sap_rows.sort(key=lambda x: x['ready_rate'])
    java_rows.sort(key=lambda x: x['ready_rate'])
    modal_data = []  # collect rows that need modals
    mi = 0
    for r in sap_rows:
        sc = 'badge-blue'
        rc = _acc_rate_badge(r['ready_rate'])
        fs_diff = r['total_done'] - r.get('fs_doc_ok', 0)
        fs_missing = r.get('fs_doc_missing_tasks', [])
        fa_diff = r['total_done'] - r.get('fs_attach_ok', 0)
        fa_missing = r.get('fs_attach_missing_tasks', [])
        if fs_diff > 0 and fs_missing:
            mid = f'acc_fs_modal_{mi}'
            fd_cell = f'<span class="fs-diff-link" onclick="openModal(\'{mid}\')">{fs_diff}</span>'
            modal_data.append({'id': mid, 'project': r['project'], 'system': r['system'], 'label': '缺失FS文档', 'missing': fs_missing})
            mi += 1
        else:
            fd_cell = str(fs_diff)
        if fa_diff > 0 and fa_missing:
            mid = f'acc_fs_modal_{mi}'
            fa_cell = f'<span class="fs-diff-link" onclick="openModal(\'{mid}\')">{fa_diff}</span>'
            modal_data.append({'id': mid, 'project': r['project'], 'system': r['system'], 'label': '缺失FS附件', 'missing': fa_missing})
            mi += 1
        else:
            fa_cell = str(fa_diff)
        P.append(f'<tr><td><span class="badge {sc}">SAP</span></td><td style="text-align:left;font-weight:500">{r["project"]}</td><td>{r["total_done"]}</td><td>{r["bt_complete"]}</td><td>{r.get("fs_doc_ok", "-")}</td><td>{fd_cell}</td><td>{r.get("fs_attach_ok", "-")}</td><td>{fa_cell}</td><td>{r["sys_test_ok"]}</td><td>{r.get("sys_test_attach_ok", "-")}</td><td>{r.get("ts_doc_ok", "-")}</td><td>{r.get("ts_attach_ok", "-")}</td></tr>')
    _render_acc_subtotal(P, sap_rows, '📊 SAP 小计')
    for r in java_rows:
        sc = 'badge-purple'
        rc = _acc_rate_badge(r['ready_rate'])
        fs_diff = r['total_done'] - r.get('fs_doc_ok', 0)
        fs_missing = r.get('fs_doc_missing_tasks', [])
        fa_diff = r['total_done'] - r.get('fs_attach_ok', 0)
        fa_missing = r.get('fs_attach_missing_tasks', [])
        if fs_diff > 0 and fs_missing:
            mid = f'acc_fs_modal_{mi}'
            fd_cell = f'<span class="fs-diff-link" onclick="openModal(\'{mid}\')">{fs_diff}</span>'
            modal_data.append({'id': mid, 'project': r['project'], 'system': r['system'], 'label': '缺失FS文档', 'missing': fs_missing})
            mi += 1
        else:
            fd_cell = str(fs_diff)
        if fa_diff > 0 and fa_missing:
            mid = f'acc_fs_modal_{mi}'
            fa_cell = f'<span class="fs-diff-link" onclick="openModal(\'{mid}\')">{fa_diff}</span>'
            modal_data.append({'id': mid, 'project': r['project'], 'system': r['system'], 'label': '缺失FS附件', 'missing': fa_missing})
            mi += 1
        else:
            fa_cell = str(fa_diff)
        P.append(f'<tr><td><span class="badge {sc}">JAVA-专业系统</span></td><td style="text-align:left;font-weight:500">{r["project"]}</td><td>{r["total_done"]}</td><td>{r["bt_complete"]}</td><td>{r.get("fs_doc_ok", "-")}</td><td>{fd_cell}</td><td>{r.get("fs_attach_ok", "-")}</td><td>{fa_cell}</td><td>{r["sys_test_ok"]}</td><td>{r.get("sys_test_attach_ok", "-")}</td><td>{r.get("ts_doc_ok", "-")}</td><td>{r.get("ts_attach_ok", "-")}</td></tr>')
    _render_acc_subtotal(P, java_rows, '📊 JAVA 小计')
    _render_acc_subtotal(P, rows, '📊 合计', is_grand=True)
    P.append('</table></div></details>')
    # Render modals for FS diff
    _render_acc_modals(P, modal_data)


def _render_acc_modals(P, modal_data):
    """Render FS document/attachment diff detail modals."""
    for m in modal_data:
        P.append(f'<div class="modal-mask" id="{m["id"]}" onclick="if(event.target===this)closeModal(\'{m["id"]}\')">')
        P.append('<div class="modal-box">')
        P.append(f'<h3>📄 {m["system"]} · {m["project"]} — {m["label"]}（{len(m["missing"])}条）</h3>')
        P.append('<button class="modal-close" onclick="closeModal(\'' + m["id"] + '\')">&times;</button>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>#</th><th>任务</th><th>模块</th><th>负责人</th><th>结束日期</th></tr>')
        for ti, t in enumerate(m['missing'], 1):
            P.append(f'<tr><td>{ti}</td><td style="text-align:left;max-width:300px">{t["task"]}</td><td>{t["module"]}</td><td>{t["person"]}</td><td>{t["end_date"]}</td></tr>')
        P.append('</table></div></div></div>')


# ============================================================
# 生成函数
# ============================================================
def generate_quality_html(d, output_path, main_report_filename=''):
    """生成数据质量专项报告 HTML

    Args:
        d: compute_all_stats 返回的完整数据字典
        output_path: 输出文件路径
        main_report_filename: 主报告文件名（用于跨报告链接，可选）
    """
    P = []  # parts

    # ===== quality 数据提取 =====
    q = d.get('quality', {})
    is_rich = 'summary' in q
    summary = q['summary'] if is_rich else q
    total_issues = q.get('total_issues', sum(v['count'] for v in summary.values())) if is_rich else sum(v['count'] for v in summary.values())

    # ===== 必填字段完整度概算 =====
    field_comp = d.get('field_comp_all', [])
    avg_field_rate = round(sum(f['rate'] for f in field_comp) / len(field_comp), 1) if field_comp else 0

    # ===== 验收就绪概算 =====
    acc_summary = d.get('acc_summary', [])
    total_done_all = sum(a['total_done'] for a in acc_summary)
    total_ready_all = sum(a['all_ready'] for a in acc_summary)
    avg_ready_rate = round(total_ready_all / total_done_all * 100, 1) if total_done_all > 0 else 0

    # ===== HTML 头部 =====
    P.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">')
    P.append('<title>1455项目 数据质量专项报告</title>')
    P.append('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>')
    P.append('<style>' + CSS + '</style>\n</head>\n<body>')

    # Header
    P.append('<div class="header"><h1>1455项目 — 数据质量专项报告</h1>')
    P.append(f'<div class="sub">数据截止: {d["report_date"]} | 报告生成: {d["generated_at"]} | 三类维度 · 独立呈现</div>')
    if main_report_filename:
        P.append(f'<a class="back-link" href="{main_report_filename}">← 返回主报告</a>')
    P.append('</div>')
    P.append('<div class="container">')

    # ===== 质量总览 KPI =====
    P.append('<div class="kpi-grid">')
    q_cls = 'green' if total_issues == 0 else 'red'
    P.append(f'<div class="kpi-card {q_cls}"><div class="label">🔍 规范违规</div><div class="value">{total_issues}</div></div>')
    f_cls = 'green' if avg_field_rate >= 95 else ('orange' if avg_field_rate >= 80 else 'red')
    P.append(f'<div class="kpi-card {f_cls}"><div class="label">📋 必填字段完整度</div><div class="value">{avg_field_rate}%</div></div>')
    a_cls = 'green' if avg_ready_rate >= 80 else ('orange' if avg_ready_rate >= 50 else 'red')
    P.append(f'<div class="kpi-card {a_cls}"><div class="label">✅ 验收就绪率</div><div class="value">{avg_ready_rate}%</div></div>')
    P.append(f'<div class="kpi-card blue"><div class="label">📦 必填字段数</div><div class="value">{d.get("required_count", 0)}</div></div>')
    P.append('</div>')

    # ================================================================
    # 一、填写规范违规
    # ================================================================
    P.append('<div class="section" style="border-left:4px solid #7c3aed"><h2>一、填写规范违规 — 8 类检查规则</h2>')
    if total_issues == 0:
        P.append('<div class="alert alert-success">✅ 数据质量检查全部通过</div>')
    else:
        P.append(f'<div class="alert alert-warn">⚠️ 发现 <strong>{total_issues}</strong> 项数据质量问题，覆盖 <strong>8</strong> 类检查规则</div>')

        # 质量KPI卡片
        issue_labels = {
            'placeholder_violations': '占位符违规',
            'status_progress_mismatch': '状态-进度不一致',
            'date_format_issues': '日期异常',
            'task_cycle_exceeded': '任务周期超标',
            'conditional_missing': '条件必填缺失',
            'phase_flow_issues': '阶段流程异常',
            'system_field_missing': '系统特有字段缺失',
            'required_field_missing': '必填字段缺失',
        }
        P.append('<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">')
        for key, label in issue_labels.items():
            if key in summary:
                count = summary[key]['count'] if isinstance(summary[key], dict) else 0
                cls = 'green' if count == 0 else 'red'
                P.append(f'<div class="kpi-card {cls}"><div class="label">{label}</div><div class="value">{count}</div></div>')
        P.append('</div>')

        # 检查规则说明
        P.append('<details style="margin:16px 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px">')
        P.append('<summary style="cursor:pointer;font-weight:700;font-size:15px;color:#1e293b">📖 检查规则说明（展开查看每类问题的含义）</summary>')
        P.append('<div class="table-wrap" style="margin-top:12px"><table>')
        P.append('<tr><th style="width:13%">检查项</th><th style="width:32%">检查规则</th><th style="width:30%">违规样例</th><th style="width:25%">违规模板/阈值</th></tr>')

        rule_descriptions = {
            'placeholder_violations': (
                '占位符违规',
                '检查必填字段中是否填写了无效占位符（如 "N/A"、"null"、"None"）。注意："-" 是模板标准空值标记，但如果用于必填字段也作为违规处理。',
                'FS文档="N/A"、进度="null"',
                '禁止值：<code>N/A</code>、<code>NA</code>、<code>null</code>、<code>None</code><br><code>-</code> 在必填字段中也视为违规<br>检查范围：★必填 + #必须 + ●SAP + ●JAVA 字段',
            ),
            'status_progress_mismatch': (
                '状态-进度不一致',
                '任务状态与进度应满足联动规则。例如：状态="已完成"但进度≠100%，状态="待处理"但进度≠0%。这种不一致会导致完成率统计失真。',
                '状态="已完成" + 进度="50%"',
                '已完成/已取消 → 进度必须=100%<br>待处理/未开始 → 进度必须=0%',
            ),
            'date_format_issues': (
                '日期格式异常',
                '所有日期字段应统一使用 YYYY/MM/DD 格式（如 2026/07/31）。不符合此格式的日期可能导致排序、筛选、计算错误。',
                '日期="2026.7.31" 或 "7/31/2026"',
                '标准格式：<code>YYYY/MM/DD</code><br>检查范围：开始日期、结束日期、FS日期、业务测试日期、TS日期',
            ),
            'task_cycle_exceeded': (
                '任务周期超标',
                '单任务计划周期（结束日期 - 开始日期）超过10个工作日上限。周期过长的任务建议拆分为更小的可管理单元。',
                '任务周期=15天',
                '上限：<code>10</code> 个工作日<br>周期=工作日天数（扣除周末）',
            ),
            'conditional_missing': (
                '条件必填缺失',
                '有条件必填字段（#必须）在触发条件下必须填写，但当前为空。例如：FS状态="已完成"时，FS实际结束日期和FS文档必须填写。',
                'FS状态=已完成 → FS文档=空',
                'FS已完成 → FS实际结束日期、FS文档必填<br>业务测试已完成 → 业务测试实际开始/结束日期必填',
            ),
            'system_field_missing': (
                '系统特有字段缺失',
                '不同系统类型（SAP / JAVA-专业系统）有各自的特有字段要求，但当前未填写。SAP系统需要TS相关字段；JAVA系统需要测试报告字段。',
                'SAP任务 → TS文档=空 / JAVA任务 → 系统测试报告=空',
                '●SAP：TS计划结束日期、TS实际结束日期、TS文档<br>●JAVA：系统测试报告、集成测试报告<br>●回归测试：仅JAVA且需求类型=修改/空时必填',
            ),
            'phase_flow_issues': (
                '阶段流程异常',
                '检查任务阶段流程是否符合 FS→业务测试→TS 的顺序逻辑。FS已完成但业务测试状态仍为空（未进入下一阶段），或业务测试已完成(SAP)但TS状态为空。',
                'FS已完成 → 业务测试状态=空 / 业务测试已完成(SAP) → TS状态=空',
                'FS已完成 → 业务测试状态必须填写<br>SAP + 业务测试已完成 → TS状态必须填写',
            ),
            'required_field_missing': (
                '必填字段缺失',
                '检查全部★必填字段是否为空。与"条件必填缺失"不同，此检查覆盖所有必填字段，无论任务状态如何。缺失最多的字段是重点整治方向。',
                '任务编号=空、功能模块=空、负责人=空',
                '模板定义的全部★必填字段逐一检查<br>详见下方"必填字段缺失明细"表',
            ),
        }

        for key, (name, rule_desc, example, threshold) in rule_descriptions.items():
            if key in summary:
                count = summary[key]['count'] if isinstance(summary[key], dict) else 0
                has_issues = count > 0
                row_style = 'style="background:#fff5f5"' if has_issues else ''
                count_badge = f'<span class="badge badge-red">{count}</span>' if has_issues else '<span class="badge badge-green">0</span>'
                P.append(f'<tr {row_style}><td style="font-weight:600;white-space:nowrap">{name} {count_badge}</td>')
                P.append(f'<td style="text-align:left;font-size:13px;line-height:1.6">{rule_desc}</td>')
                P.append(f'<td style="text-align:left;font-size:12px;color:#dc2626"><code>{example}</code></td>')
                P.append(f'<td style="text-align:left;font-size:12px;line-height:1.6">{threshold}</td></tr>')
        P.append('</table></div>')
        P.append('</details>')

        # 质量分类柱状图
        P.append('<div class="chart-row"><div class="chart-box" style="grid-column:1/-1"><h3>各类质量问题分布</h3><canvas id="qualityBarChart"></canvas></div></div>')

        # 违规样例展示
        sample_labels_ordered = [
            ('placeholder_violations', '占位符违规'),
            ('status_progress_mismatch', '状态-进度不一致'),
            ('date_format_issues', '日期异常'),
            ('task_cycle_exceeded', '任务周期超标'),
            ('conditional_missing', '条件必填缺失'),
            ('phase_flow_issues', '阶段流程异常'),
            ('system_field_missing', '系统特有字段缺失'),
            ('required_field_missing', '必填字段缺失'),
        ]
        P.append('<details style="margin:16px 0;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:16px">')
        P.append('<summary style="cursor:pointer;font-weight:700;font-size:15px;color:#991b1b">🔍 违规样例（展开查看每类问题的典型记录，每类最多5条）</summary>')
        for key, label in sample_labels_ordered:
            items = summary.get(key, {}).get('items', []) if isinstance(summary.get(key), dict) else []
            if not items:
                continue
            count = summary[key]['count'] if isinstance(summary[key], dict) else len(items)
            show_items = items[:5]
            P.append(f'<h4 style="margin:12px 0 6px;color:#dc2626">{label}（共 {count} 条，展示前 {len(show_items)} 条）</h4>')
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th style="width:5%">#</th><th style="width:20%">项目</th><th style="width:8%">批次</th><th style="width:10%">系统</th><th style="width:30%">任务名称</th><th style="width:27%">具体问题描述</th></tr>')
            for i, item in enumerate(show_items):
                prj = item.get('project', '')
                bat = item.get('batch', '')
                sys = item.get('system', '')
                tsk = item.get('task', '')[:50]
                iss = item.get('issue', '')
                P.append(f'<tr><td>{i+1}</td><td style="text-align:left;font-size:12px">{prj}</td><td>{bat}</td><td>{sys}</td><td style="text-align:left;font-size:12px;max-width:250px">{tsk}</td><td style="text-align:left;font-size:12px;color:#b91c1c"><code>{iss}</code></td></tr>')
            P.append('</table></div>')
        P.append('</details>')

        # 必填字段缺失明细（逐字段展开）
        req_field_summary = q.get('required_field_summary', [])
        total_req_missing = q.get('summary', {}).get('required_field_missing', {}).get('count', 0) if is_rich else 0
        total_tasks_all = d.get('total_tasks', len(d.get('all_records', [])))
        if req_field_summary and total_req_missing > 0:
            P.append('<details style="margin:16px 0;background:#fff7ed;border:1px solid #fdba74;border-radius:8px;padding:16px">')
            P.append('<summary style="cursor:pointer;font-weight:700;font-size:15px;color:#9a3412">📊 必填字段缺失明细（按字段逐个统计，共 {} 条缺失 · 共 {} 条记录）</summary>'.format(total_req_missing, total_tasks_all))
            P.append('<div class="table-wrap" style="margin-top:12px"><table>')
            P.append('<tr><th>排名</th><th>必填字段</th><th>缺失次数</th><th>缺失率</th><th>占必填缺失比</th><th>受影响项目数</th></tr>')
            for i, item in enumerate(req_field_summary):
                pct_val = round(item['count'] / total_req_missing * 100, 1) if total_req_missing > 0 else 0
                miss_rate = item.get('missing_rate', round(item['count'] / max(total_tasks_all, 1) * 100, 1))
                num_proj = item.get('num_projects', 0)
                cls = 'badge-red' if item['count'] > 200 else ('badge-yellow' if item['count'] > 50 else 'badge-green')
                rate_cls = 'badge-red' if miss_rate > 30 else ('badge-yellow' if miss_rate > 10 else 'badge-green')
                P.append(f'<tr><td>{i+1}</td><td style="text-align:left;font-weight:600">{item["field"]}</td><td><span class="badge {cls}">{item["count"]}</span></td><td><span class="badge {rate_cls}">{miss_rate}%</span></td><td>{pct_val}%</td><td>{num_proj}</td></tr>')
            P.append('</table></div>')
            # 逐字段项目分布明细
            P.append('<h4 style="margin:16px 0 8px;color:#9a3412">📋 各字段受影响项目分布（展开查看每个字段缺失集中在哪些项目）</h4>')
            for i, item in enumerate(req_field_summary):
                top_projs = item.get('top_projects', [])
                if not top_projs:
                    continue
                total_for_field = item['count']
                P.append(f'<details style="margin:8px 0;background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px">')
                P.append('<summary style="cursor:pointer;font-weight:600;font-size:14px;color:#92400e">🔹 {} — 缺失 {} 次（{} 个项目受影响）</summary>'.format(item['field'], item['count'], item.get('num_projects', len(top_projs))))
                P.append('<div class="table-wrap" style="margin-top:8px"><table>')
                P.append('<tr><th>#</th><th>项目</th><th>缺失次数</th><th>占该字段缺失比</th></tr>')
                for j, tp in enumerate(top_projs):
                    tp_pct = round(tp['count'] / total_for_field * 100, 1) if total_for_field > 0 else 0
                    tp_cls = 'badge-red' if tp['count'] > 50 else ('badge-yellow' if tp['count'] > 10 else 'badge-green')
                    P.append(f'<tr><td>{j+1}</td><td style="text-align:left">{tp["project"]}</td><td><span class="badge {tp_cls}">{tp["count"]}</span></td><td>{tp_pct}%</td></tr>')
                P.append('</table></div></details>')
            P.append('</details>')

        if is_rich:
            # 批次×系统类型 质量分布
            if q.get('by_batch_system'):
                P.append('<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">1.1 批次 × 系统类型 质量问题分布</summary>')
                P.append('<div class="table-wrap"><table>')
                P.append('<tr><th>批次</th><th>系统类型</th><th>问题总数</th><th>占位符</th><th>状态进度</th><th>日期异常</th><th>周期超标</th><th>条件必填</th><th>阶段流程</th><th>系统字段</th><th>必填缺失</th></tr>')
                for r in q['by_batch_system']:
                    total = r['total']
                    cls = 'badge-red' if total > 100 else ('badge-yellow' if total > 50 else 'badge-green')
                    P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["system"]}</td><td><span class="badge {cls}">{total}</span></td><td>{r.get("placeholder_violations",0)}</td><td>{r.get("status_progress_mismatch",0)}</td><td>{r.get("date_format_issues",0)}</td><td>{r.get("task_cycle_exceeded",0)}</td><td>{r.get("conditional_missing",0)}</td><td>{r.get("phase_flow_issues",0)}</td><td>{r.get("system_field_missing",0)}</td><td>{r.get("required_field_missing",0)}</td></tr>')
                P.append('</table></div></details>')

            # 项目质量问题排名（全量）
            if q.get('by_project'):
                top_proj = q['by_project']
                P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">1.2 项目质量问题排名（共 {len(top_proj)} 个项目）</summary>')
                P.append('<div class="table-wrap"><table>')
                P.append('<tr><th>排名</th><th>项目</th><th>问题总数</th><th>占位符</th><th>状态进度</th><th>日期异常</th><th>周期超标</th><th>条件必填</th><th>阶段流程</th><th>系统字段</th><th>必填缺失</th></tr>')
                for i, r in enumerate(top_proj):
                    total = r['total']
                    cls = 'badge-red' if total > 100 else ('badge-yellow' if total > 50 else 'badge-green')
                    P.append(f'<tr><td><strong>{i+1}</strong></td><td style="text-align:left">{r["project"]}</td><td><span class="badge {cls}">{total}</span></td><td>{r.get("placeholder_violations",0)}</td><td>{r.get("status_progress_mismatch",0)}</td><td>{r.get("date_format_issues",0)}</td><td>{r.get("task_cycle_exceeded",0)}</td><td>{r.get("conditional_missing",0)}</td><td>{r.get("phase_flow_issues",0)}</td><td>{r.get("system_field_missing",0)}</td><td>{r.get("required_field_missing",0)}</td></tr>')
                P.append('</table></div></details>')

            # 问题最多的任务（全量）
            if q.get('top_tasks'):
                top_ts = q['top_tasks']
                P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">1.3 质量问题最多的任务（共 {len(top_ts)} 条）</summary>')
                P.append('<div class="table-wrap"><table>')
                P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>任务名称</th><th>问题数</th></tr>')
                for i, t in enumerate(top_ts):
                    ic = 'badge-red' if t['issues'] >= 3 else 'badge-yellow'
                    P.append(f'<tr><td>{i+1}</td><td style="text-align:left">{t["project"]}</td><td>{t["batch"]}</td><td>{t["system"]}</td><td style="text-align:left;max-width:300px">{t["task"]}</td><td><span class="badge {ic}">{t["issues"]}</span></td></tr>')
                P.append('</table></div></details>')
    P.append('</div>')

    # ================================================================
    # 二、必填字段完整度
    # ================================================================
    P.append('<div class="section" style="border-left:4px solid #d97706"><h2>二、必填字段完整度 — 批次 × 系统类型</h2>')
    P.append(f'<div class="alert alert-warn">模板定义 <strong>{d["required_count"]} 个必填字段</strong>（★必填）。</div>')

    # 2.1 各字段填写率
    P.append('<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">2.1 各字段填写率</summary><div class="table-wrap"><table>')
    P.append('<tr><th>字段名</th><th>已填写</th><th>缺失</th><th>完整度</th></tr>')
    for f in sorted(field_comp, key=lambda x: x['rate']):
        rc = 'badge-green' if f['rate'] >= 95 else ('badge-yellow' if f['rate'] >= 80 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{f["field"]}</td><td>{f["filled"]}</td><td><span class="badge badge-red">{f["missing"]}</span></td><td><span class="badge {rc}">{f["rate"]}%</span></td></tr>')
    P.append('</table></div></details>')

    # 2.1.1 项目字段完整度排名
    fcp = d.get('field_comp_by_project', [])
    if fcp:
        top_fcp = fcp
        P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">2.1.1 项目字段完整度排名（共 {len(top_fcp)} 个项目，完整度升序）</summary>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>排名</th><th>项目</th><th>批次</th><th>系统</th><th>总任务</th><th>平均完整度</th><th>100%完整记录</th><th>100%占比</th></tr>')
        for i, r in enumerate(top_fcp):
            rc = 'badge-green' if r['avg_rate'] >= 95 else ('badge-yellow' if r['avg_rate'] >= 80 else 'badge-red')
            P.append(f'<tr><td>{i+1}</td><td style="text-align:left;font-weight:600">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total_tasks"]}</td><td><span class="badge {rc}">{r["avg_rate"]}%</span></td><td>{r["perfect"]}</td><td>{r["perfect_rate"]}%</td></tr>')
        P.append('</table></div></details>')

    # 2.2 批次×系统类型 完整度
    P.append('<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">2.2 批次 × 系统类型 完整度</summary><div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>系统</th><th>总任务</th><th>平均完整率</th><th>100%完整记录</th><th>100%占比</th></tr>')
    for r in d['batch_system_field_comp']:
        rc = 'badge-green' if r['avg_rate'] >= 95 else ('badge-yellow' if r['avg_rate'] >= 80 else 'badge-red')
        P.append(f'<tr><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td><span class="badge {rc}">{r["avg_rate"]}%</span></td><td>{r["perfect"]}</td><td>{r["perfect_rate"]}%</td></tr>')
    P.append('</table></div></details>')

    # 2.3 未完成任务必填字段缺失 Top 50
    undone_issues = d.get('undone_field_issues', [])
    if undone_issues:
        P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">2.3 未完成任务必填字段缺失（{len(undone_issues)}条）</summary>')
        P.append('<div class="alert alert-info">💡 点击「缺失数」徽章可查看该任务的完整详细信息与缺失字段清单。</div>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>任务</th><th>状态</th><th>负责人</th><th>缺失数</th><th>缺失字段</th></tr>')
        for i, iss in enumerate(undone_issues):
            mc = 'badge-red' if iss['missing_count'] >= 5 else 'badge-yellow'
            P.append(f'<tr><td>{i + 1}</td><td style="text-align:left">{iss["project"]}</td><td>{iss["batch"]}</td><td>{iss["system"]}</td><td style="text-align:left;max-width:250px">{iss["task"]}</td><td>{iss["status"]}</td><td>{iss["person"]}</td><td><span class="badge {mc} clickable-badge" onclick="showUndoneDetail({i})" title="点击查看详细信息">{iss["missing_count"]}</span></td><td style="text-align:left;font-size:11px">{iss["missing_fields"]}</td></tr>')
        P.append('</table></div></details>')

    # 2.4 已完成任务必填字段缺失
    done_issues = d.get('done_field_issues', [])
    if done_issues:
        P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">2.4 已完成任务必填字段缺失（{len(done_issues)}条）</summary>')
        P.append('<div class="alert alert-info">💡 点击「缺失数」徽章可查看该任务的完整详细信息与缺失字段清单。</div>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>任务</th><th>状态</th><th>负责人</th><th>缺失数</th><th>缺失字段</th></tr>')
        for i, iss in enumerate(done_issues):
            mc = 'badge-red' if iss['missing_count'] >= 5 else 'badge-yellow'
            P.append(f'<tr><td>{i + 1}</td><td style="text-align:left">{iss["project"]}</td><td>{iss["batch"]}</td><td>{iss["system"]}</td><td style="text-align:left;max-width:250px">{iss["task"]}</td><td>{iss["status"]}</td><td>{iss["person"]}</td><td><span class="badge {mc} clickable-badge" onclick="showDoneDetail({i})" title="点击查看详细信息">{iss["missing_count"]}</span></td><td style="text-align:left;font-size:11px">{iss["missing_fields"]}</td></tr>')
        P.append('</table></div></details>')
    P.append('</div>')

    # ================================================================
    # 三、验收就绪分析
    # ================================================================
    P.append('<div class="section" style="border-left:4px solid #16a34a"><h2>三、交付物就绪分析 — FS & 功能测试报告 & TS</h2>')
    P.append('<div class="alert alert-info">验收需关注：FS、系统测试报告、TS等。</div>')

    # 3.1 A批次交付物 系统类型 X 项目 - 完成进度
    acc_a = [a for a in acc_summary if a['batch'] == 'A批次']
    _render_acc_matrix(P, acc_a, '3.1 A批次交付物 系统类型 × 项目 — 完成进度')

    # 3.2 验收材料不全的已完成任务
    acceptance = d.get('acceptance', [])
    acc_incomplete = [a for a in acceptance if not a['all_ready']]
    P.append(f'<details><summary style="cursor:pointer;font-weight:700;font-size:16px;color:#374151;margin:20px 0 12px">3.2 验收材料不全的已完成任务（{len(acc_incomplete)}条，需补充）</summary>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>结束日期</th><th>业务测试</th><th>系统测试</th><th>系统附件</th><th>集成测试</th><th>集成附件</th><th>回归测试</th><th>回归附件</th><th>缺失项</th></tr>')
    for a in acc_incomplete:
        missing = []
        if a['bt_status'] != '已完成':
            missing.append('业务测试')
        if a['sys_test'] == '❌':
            missing.append('系统测试报告')
        if a.get('sys_test_attach', '❌') == '❌':
            missing.append('系统测试附件')
        if a['integ_test'] == '❌':
            missing.append('集成测试报告')
        if a.get('integ_test_attach', '❌') == '❌':
            missing.append('集成测试附件')
        if a['regr_test'] == '❌':
            missing.append('回归测试报告')
        if a.get('regr_test_attach', '❌') == '❌':
            missing.append('回归测试附件')
        P.append(f'<tr><td style="text-align:left">{a["project"]}</td><td>{a["batch"]}</td><td>{a["system"]}</td><td>{a["module"]}</td><td style="text-align:left;max-width:200px">{a["task"]}</td><td>{a["end_date"]}</td><td>{a["bt_status"]}</td><td>{a["sys_test"]}</td><td>{a.get("sys_test_attach", "-")}</td><td>{a["integ_test"]}</td><td>{a.get("integ_test_attach", "-")}</td><td>{a["regr_test"]}</td><td>{a.get("regr_test_attach", "-")}</td><td style="text-align:left;font-size:11px">{", ".join(missing)}</td></tr>')
    P.append('</table></div></details></div>')

    # ================================================================
    # 四、项目质量全景排名 — 融合完整度 + 8 类违规 + 缺失字段
    # ================================================================
    P.append('<div class="section" style="border-left:4px solid #dc2626"><h2>四、项目质量全景排名 — 全项目 × 全维度</h2>')
    P.append('<details><summary style="cursor:pointer;font-weight:700;font-size:15px;color:#374151;margin:10px 0">展开查看全景排名表</summary>')
    P.append('<div class="alert alert-info">综合展示每个项目的字段完整度与 8 类质量违规数量，按总问题数降序排列。最后一列标注该项目缺失最多的具体字段，便于定位整改重点。</div>')

    # 构建项目→违规计数映射
    from collections import Counter, defaultdict
    proj_quality_map = {}
    if is_rich:
        for r in q.get('by_project', []):
            proj_quality_map[r['project']] = r

    # 项目→字段缺失统计（从违规明细中聚合）
    proj_field_missing = defaultdict(Counter)
    for check_key in ['conditional_missing', 'system_field_missing', 'required_field_missing']:
        items = summary.get(check_key, {})
        if isinstance(items, dict):
            items = items.get('items', [])
        for item in items:
            if check_key == 'required_field_missing':
                short = item.get('field', '')
            else:
                field = item.get('field', '') or item.get('condition', '') or item.get('issue', '')
                short = ''
                if field:
                    short = field.replace('未填写', '').replace('必填', '').replace('SAP系统 - ', '').replace('JAVA-专业系统 - ', '').replace('FS状态=已完成 → ', '').replace('TS状态=已完成 → ', '').replace('业务测试状态=已完成 → ', '').strip()
            if short:
                proj_field_missing[item['project']][short] += 1

    # 合并完整度
    fcp_map = {}
    for r in fcp:
        fcp_map[r['project']] = r

    all_projects = sorted(set(list(proj_quality_map.keys()) + list(fcp_map.keys())))
    combined = []
    for proj in all_projects:
        qr = proj_quality_map.get(proj, {})
        fr = fcp_map.get(proj, {})
        top_fields = proj_field_missing.get(proj, Counter()).most_common(5)
        combined.append({
            'project': proj,
            'batch': qr.get('batch', fr.get('batch', '')),
            'system': qr.get('system', fr.get('system', '')),
            'total_tasks': fr.get('total_tasks', 0),
            'avg_rate': fr.get('avg_rate', 0),
            'perfect': fr.get('perfect', 0),
            'perfect_rate': fr.get('perfect_rate', 0),
            'placeholder': qr.get('placeholder_violations', 0),
            'status_progress': qr.get('status_progress_mismatch', 0),
            'date_format': qr.get('date_format_issues', 0),
            'task_cycle': qr.get('task_cycle_exceeded', 0),
            'conditional': qr.get('conditional_missing', 0),
            'phase_flow': qr.get('phase_flow_issues', 0),
            'system_field': qr.get('system_field_missing', 0),
            'required_field': qr.get('required_field_missing', 0),
            'total_issues': qr.get('total', 0),
            'top_missing': ', '.join(f'{f}×{c}' for f, c in top_fields) if top_fields else '-',
        })
    combined.sort(key=lambda x: x['total_issues'], reverse=True)

    # 汇总行
    sum_row = {
        'project': '【合计】', 'batch': '', 'system': '',
        'total_tasks': sum(r['total_tasks'] for r in combined),
        'avg_rate': round(sum(r['avg_rate'] * r['total_tasks'] for r in combined) / max(sum(r['total_tasks'] for r in combined), 1), 1),
        'perfect': sum(r['perfect'] for r in combined),
        'perfect_rate': 0,
        'placeholder': sum(r['placeholder'] for r in combined),
        'status_progress': sum(r['status_progress'] for r in combined),
        'date_format': sum(r['date_format'] for r in combined),
        'task_cycle': sum(r['task_cycle'] for r in combined),
        'conditional': sum(r['conditional'] for r in combined),
        'phase_flow': sum(r['phase_flow'] for r in combined),
        'system_field': sum(r['system_field'] for r in combined),
        'required_field': sum(r['required_field'] for r in combined),
        'total_issues': sum(r['total_issues'] for r in combined),
        'top_missing': '',
    }

    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>排名</th><th>项目</th><th>批次</th><th>系统</th><th>任务数</th><th>完整度</th><th>占位符</th><th>状态进度</th><th>日期异常</th><th>周期超标</th><th>条件缺失</th><th>阶段流程</th><th>系统字段</th><th>必填缺失</th><th style="color:#dc2626">总问题</th><th>最缺失字段(Top5)</th></tr>')

    def _render_combined_row(r, is_summary=False):
        rc = 'badge-green' if r['avg_rate'] >= 95 else ('badge-yellow' if r['avg_rate'] >= 80 else 'badge-red')
        ic = 'badge-red' if r['total_issues'] > 100 else ('badge-yellow' if r['total_issues'] > 50 else 'badge-green')
        style = 'style="font-weight:700;background:#fef2f2"' if is_summary else ''
        return f'<tr {style}><td>{"" if is_summary else ""}</td><td style="text-align:left;font-weight:600">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total_tasks"]}</td><td><span class="badge {rc}">{r["avg_rate"]}%</span></td><td>{r["placeholder"]}</td><td>{r["status_progress"]}</td><td>{r["date_format"]}</td><td>{r["task_cycle"]}</td><td>{r["conditional"]}</td><td>{r["phase_flow"]}</td><td>{r["system_field"]}</td><td>{r["required_field"]}</td><td><span class="badge {ic}">{r["total_issues"]}</span></td><td style="text-align:left;font-size:11px;max-width:250px">{r["top_missing"]}</td></tr>'

    for i, r in enumerate(combined):
        P.append(_render_combined_row(r).replace('<td></td>', f'<td>{i+1}</td>', 1))
    P.append(_render_combined_row(sum_row, is_summary=True))
    P.append('</table></div>')
    P.append('</details></div>')

    # Footer
    P.append(f'<div class="footer"><p>1455项目 数据质量专项报告 | 自动生成于 {d["generated_at"]} | 数据截止 {d["report_date"]}</p><p>本报告由 PMO 分析工具自动生成，与主报告共享同一数据源。</p></div></div>')

    # ===== 2.3 任务详情弹窗（点击缺失数触发） =====
    def _clean_val(v):
        s = str(v).strip()
        return '-' if s in ('', 'nan', 'None', 'NaT') else s

    undone_detail_data = []
    for iss in undone_issues:
        missing_list = iss.get('missing_list') or [f.strip() for f in iss.get('missing_fields', '').split(',') if f.strip()]
        undone_detail_data.append({
            'task_full': _clean_val(iss.get('task_full', iss.get('task', ''))),
            'project': _clean_val(iss.get('project')), 'batch': _clean_val(iss.get('batch')),
            'system': _clean_val(iss.get('system')), 'module': _clean_val(iss.get('module', '')),
            'type': _clean_val(iss.get('type', '')), 'priority': _clean_val(iss.get('priority', '')),
            'select_type': _clean_val(iss.get('select_type', '')), 'desc': _clean_val(iss.get('desc', '')),
            'status': _clean_val(iss.get('status')), 'progress': _clean_val(iss.get('progress', '')),
            'person': _clean_val(iss.get('person')), 'plan_days': _clean_val(iss.get('plan_days', '')),
            'start': _clean_val(iss.get('start', '')), 'end': _clean_val(iss.get('end', '')),
            'fs_status': _clean_val(iss.get('fs_status', '')), 'fs_person': _clean_val(iss.get('fs_person', '')),
            'fs_plan_end': _clean_val(iss.get('fs_plan_end', '')),
            'bt_status': _clean_val(iss.get('bt_status', '')), 'bt_person': _clean_val(iss.get('bt_person', '')),
            'bt_plan_start': _clean_val(iss.get('bt_plan_start', '')), 'bt_plan_end': _clean_val(iss.get('bt_plan_end', '')),
            'ts_status': _clean_val(iss.get('ts_status', '')),
            'ts_plan_end': _clean_val(iss.get('ts_plan_end', '')),
            'ts_actual_end': _clean_val(iss.get('ts_actual_end', '')),
            'ts_doc': _clean_val(iss.get('ts_doc', '')),
            'ts_attach': _clean_val(iss.get('ts_attach', '')),
            'sys_test': _clean_val(iss.get('sys_test', '')),
            'integ_test': _clean_val(iss.get('integ_test', '')),
            'sys_test_attach': _clean_val(iss.get('sys_test_attach', '')),
            'integ_test_attach': _clean_val(iss.get('integ_test_attach', '')),
            'delay_reason': _clean_val(iss.get('delay_reason', '')), 'remark': _clean_val(iss.get('remark', '')),
            'missing_count': iss.get('missing_count', len(missing_list)),
            'missing_list': missing_list,
        })
    undone_detail_json = json.dumps(undone_detail_data, ensure_ascii=False).replace('</', '<\\/')

    # 已完成任务详情数据（2.4 弹窗用）
    done_detail_data = []
    for iss in done_issues:
        missing_list = iss.get('missing_list') or [f.strip() for f in iss.get('missing_fields', '').split(',') if f.strip()]
        done_detail_data.append({
            'task_full': _clean_val(iss.get('task_full', iss.get('task', ''))),
            'project': _clean_val(iss.get('project')), 'batch': _clean_val(iss.get('batch')),
            'system': _clean_val(iss.get('system')), 'module': _clean_val(iss.get('module', '')),
            'type': _clean_val(iss.get('type', '')), 'priority': _clean_val(iss.get('priority', '')),
            'select_type': _clean_val(iss.get('select_type', '')), 'desc': _clean_val(iss.get('desc', '')),
            'status': _clean_val(iss.get('status')), 'progress': _clean_val(iss.get('progress', '')),
            'person': _clean_val(iss.get('person')), 'plan_days': _clean_val(iss.get('plan_days', '')),
            'start': _clean_val(iss.get('start', '')), 'end': _clean_val(iss.get('end', '')),
            'fs_status': _clean_val(iss.get('fs_status', '')), 'fs_person': _clean_val(iss.get('fs_person', '')),
            'fs_plan_end': _clean_val(iss.get('fs_plan_end', '')),
            'fs_actual_end': _clean_val(iss.get('fs_actual_end', '')),
            'fs_doc': _clean_val(iss.get('fs_doc', '')), 'fs_attach': _clean_val(iss.get('fs_attach', '')),
            'bt_status': _clean_val(iss.get('bt_status', '')), 'bt_person': _clean_val(iss.get('bt_person', '')),
            'bt_plan_start': _clean_val(iss.get('bt_plan_start', '')), 'bt_plan_end': _clean_val(iss.get('bt_plan_end', '')),
            'bt_actual_start': _clean_val(iss.get('bt_actual_start', '')),
            'bt_actual_end': _clean_val(iss.get('bt_actual_end', '')),
            'ts_status': _clean_val(iss.get('ts_status', '')),
            'ts_plan_end': _clean_val(iss.get('ts_plan_end', '')),
            'ts_actual_end': _clean_val(iss.get('ts_actual_end', '')),
            'ts_doc': _clean_val(iss.get('ts_doc', '')), 'ts_attach': _clean_val(iss.get('ts_attach', '')),
            'sys_test': _clean_val(iss.get('sys_test', '')),
            'integ_test': _clean_val(iss.get('integ_test', '')),
            'sys_test_attach': _clean_val(iss.get('sys_test_attach', '')),
            'integ_test_attach': _clean_val(iss.get('integ_test_attach', '')),
            'delay_reason': _clean_val(iss.get('delay_reason', '')), 'remark': _clean_val(iss.get('remark', '')),
            'missing_count': iss.get('missing_count', len(missing_list)),
            'missing_list': missing_list,
        })
    done_detail_json = json.dumps(done_detail_data, ensure_ascii=False).replace('</', '<\\/')

    P.append('''<div class="modal-mask" id="udModal" onclick="closeUndoneDetail(event)">
<div class="modal-box">
<button class="modal-close" onclick="closeUndoneDetail()" title="关闭">×</button>
<h3 id="udTitle"></h3>
<div id="udMissNote" style="font-size:12px;color:#dc2626;font-weight:600;margin:-6px 0 10px"></div>
<div class="detail-grid" id="udGrid"></div>
</div>
</div>''')
    P.append('<script>\nconst UNDONE_DETAILS = ' + undone_detail_json + ';\nconst DONE_DETAILS = ' + done_detail_json + ''';
function _esc(s){return String(s==null?'-':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function showUndoneDetail(i){
  const t = UNDONE_DETAILS[i];
  if(!t) return;
  document.getElementById('udTitle').textContent = '📋 ' + (t.task_full || '-');
  document.getElementById('udMissNote').textContent = '✕ 缺失必填字段 ' + t.missing_count + ' 个（下方红色标记）';
  const rows = [
    ['项目',t.project,null],['批次',t.batch,null],
    ['系统类型',t.system,null],['模块',t.module,null],
    ['任务类型',t.type,'任务类型'],['选择类型',t.select_type,'选择类型'],
    ['优先级',t.priority,'优先级'],['状态',t.status,'状态'],
    ['进度',t.progress,'进度'],['负责人',t.person,'负责人'],
    ['开始日期',t.start,'开始日期'],['结束日期',t.end,'结束日期'],
    ['描述',t.desc,'描述'],['计划开发人天',t.plan_days,null],
    ['FS状态',t.fs_status,'FS状态'],['FS负责人',t.fs_person,'FS负责人'],
    ['FS计划结束日期',t.fs_plan_end,'FS计划结束日期'],['FS实际结束日期',t.fs_actual_end,'FS实际结束日期'],
    ['FS文档',t.fs_doc,'FS文档'],['FS附件',t.fs_attach,'FS附件'],
    ['业务测试状态',t.bt_status,'业务测试状态'],['业务测试负责人',t.bt_person,'业务测试负责人'],
    ['业务测试计划开始日期',t.bt_plan_start,'业务测试计划开始日期'],['业务测试计划结束日期',t.bt_plan_end,'业务测试计划结束日期'],
    ['业务测试实际开始日期',t.bt_actual_start,'业务测试实际开始日期'],['业务测试实际结束日期',t.bt_actual_end,'业务测试实际结束日期'],
    ['TS状态',t.ts_status,'TS状态'],['TS计划结束日期',t.ts_plan_end,'TS计划结束日期'],
    ['TS实际结束日期',t.ts_actual_end,'TS实际结束日期'],['TS文档',t.ts_doc,'TS文档'],
    ['TS附件',t.ts_attach,'TS附件'],
    ['系统测试报告',t.sys_test,'系统测试报告'],['集成测试报告',t.integ_test,'集成测试报告'],
    ['系统测试报告附件',t.sys_test_attach,'系统测试报告附件'],['集成测试报告附件',t.integ_test_attach,'集成测试报告附件'],
    ['延期原因',t.delay_reason,null],['备注',t.remark,null]];
  const missSet = new Set(t.missing_list||[]);
  document.getElementById('udGrid').innerHTML = rows.map(r=>{
    const miss = r[2] && missSet.has(r[2]);
    return '<div class="k'+(miss?' miss':'')+'">'+r[0]+'</div><div class="v'+(miss?' miss':'')+'">'+(miss?'（未填写）':_esc(r[1]))+'</div>';
  }).join('');
  document.getElementById('udModal').classList.add('show');
}
function showDoneDetail(i){
  const t = DONE_DETAILS[i];
  if(!t) return;
  document.getElementById('udTitle').textContent = '📋 ' + (t.task_full || '-');
  document.getElementById('udMissNote').textContent = '✕ 缺失必填字段 ' + t.missing_count + ' 个（下方红色标记）';
  const rows = [
    ['项目',t.project,null],['批次',t.batch,null],
    ['系统类型',t.system,null],['模块',t.module,null],
    ['任务类型',t.type,'任务类型'],['选择类型',t.select_type,'选择类型'],
    ['优先级',t.priority,'优先级'],['状态',t.status,'状态'],
    ['进度',t.progress,'进度'],['负责人',t.person,'负责人'],
    ['开始日期',t.start,'开始日期'],['结束日期',t.end,'结束日期'],
    ['描述',t.desc,'描述'],['计划开发人天',t.plan_days,null],
    ['FS状态',t.fs_status,'FS状态'],['FS负责人',t.fs_person,'FS负责人'],
    ['FS计划结束日期',t.fs_plan_end,'FS计划结束日期'],['FS实际结束日期',t.fs_actual_end,'FS实际结束日期'],
    ['FS文档',t.fs_doc,'FS文档'],['FS附件',t.fs_attach,'FS附件'],
    ['业务测试状态',t.bt_status,'业务测试状态'],['业务测试负责人',t.bt_person,'业务测试负责人'],
    ['业务测试计划开始日期',t.bt_plan_start,'业务测试计划开始日期'],['业务测试计划结束日期',t.bt_plan_end,'业务测试计划结束日期'],
    ['业务测试实际开始日期',t.bt_actual_start,'业务测试实际开始日期'],['业务测试实际结束日期',t.bt_actual_end,'业务测试实际结束日期'],
    ['TS状态',t.ts_status,'TS状态'],['TS计划结束日期',t.ts_plan_end,'TS计划结束日期'],
    ['TS实际结束日期',t.ts_actual_end,'TS实际结束日期'],['TS文档',t.ts_doc,'TS文档'],
    ['TS附件',t.ts_attach,'TS附件'],
    ['系统测试报告',t.sys_test,'系统测试报告'],['集成测试报告',t.integ_test,'集成测试报告'],
    ['系统测试报告附件',t.sys_test_attach,'系统测试报告附件'],['集成测试报告附件',t.integ_test_attach,'集成测试报告附件'],
    ['延期原因',t.delay_reason,null],['备注',t.remark,null]];
  const missSet = new Set(t.missing_list||[]);
  document.getElementById('udGrid').innerHTML = rows.map(r=>{
    const miss = r[2] && missSet.has(r[2]);
    return '<div class="k'+(miss?' miss':'')+'">'+r[0]+'</div><div class="v'+(miss?' miss':'')+'">'+(miss?'（未填写）':_esc(r[1]))+'</div>';
  }).join('');
  document.getElementById('udModal').classList.add('show');
}
function closeUndoneDetail(e){
  if(!e || e.target === document.getElementById('udModal')) document.getElementById('udModal').classList.remove('show');
  if(e && e.target.classList.contains('modal-close')) document.getElementById('udModal').classList.remove('show');
}
document.addEventListener('keydown', e=>{ if(e.key==='Escape') document.getElementById('udModal').classList.remove('show'); });
function openModal(id){ document.getElementById(id).classList.add('show'); }
function closeModal(id){ document.getElementById(id).classList.remove('show'); }
document.addEventListener('keydown', e=>{ if(e.key==='Escape') document.querySelectorAll('.modal-mask.show').forEach(m=>m.classList.remove('show')); });
</script>''')

    # ===== Charts JS =====
    quality_labels = json.dumps(['占位符违规', '状态进度不一致', '日期异常', '任务周期超标', '条件必填缺失', '阶段流程', '系统字段缺失', '必填字段缺失'])
    if is_rich:
        quality_counts = json.dumps([
            summary.get('placeholder_violations', {}).get('count', 0) if isinstance(summary.get('placeholder_violations', {}), dict) else 0,
            summary.get('status_progress_mismatch', {}).get('count', 0) if isinstance(summary.get('status_progress_mismatch', {}), dict) else 0,
            summary.get('date_format_issues', {}).get('count', 0) if isinstance(summary.get('date_format_issues', {}), dict) else 0,
            summary.get('task_cycle_exceeded', {}).get('count', 0) if isinstance(summary.get('task_cycle_exceeded', {}), dict) else 0,
            summary.get('conditional_missing', {}).get('count', 0) if isinstance(summary.get('conditional_missing', {}), dict) else 0,
            summary.get('phase_flow_issues', {}).get('count', 0) if isinstance(summary.get('phase_flow_issues', {}), dict) else 0,
            summary.get('system_field_missing', {}).get('count', 0) if isinstance(summary.get('system_field_missing', {}), dict) else 0,
            summary.get('required_field_missing', {}).get('count', 0) if isinstance(summary.get('required_field_missing', {}), dict) else 0,
        ])
    else:
        quality_counts = json.dumps([0, 0, 0, 0, 0, 0, 0, 0])

    P.append(f'''<script>
new Chart(document.getElementById('qualityBarChart'),{{type:'bar',data:{{labels:{quality_labels},datasets:[{{label:'问题数量',data:{quality_counts},backgroundColor:['#ef4444','#f97316','#eab308','#22c55e','#06b6d4','#8b5cf6','#ec4899','#6366f1']}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true}}}}}}}});
</script></body></html>''')

    html = '\n'.join(P)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
