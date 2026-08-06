"""PMO 项目监控分析 — HTML 报告渲染"""

import json
import os
from collections import Counter

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
.alert-success{background:#dcfce7;border:1px solid #86efac;color:#166534}
.footer{text-align:center;padding:20px;color:#9ca3af;font-size:12px}
@media(max-width:768px){.chart-row{grid-template-columns:1fr}}
.dim-tag{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;margin:0 2px}
.dim-project{background:#dbeafe;color:#1e40af}
.dim-batch{background:#dcfce7;color:#166534}
.dim-system{background:#ede9fe;color:#6b21a8}
/* 执行摘要 */
.exec-summary{border-radius:12px;padding:20px 24px;margin:20px 0;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.exec-summary h2{font-size:18px;margin-bottom:16px;border:none;padding:0}
.exec-item{display:flex;align-items:flex-start;gap:10px;padding:10px 14px;margin:6px 0;border-radius:8px;font-size:13px;line-height:1.5}
.exec-item .exec-icon{flex-shrink:0;font-size:16px;margin-top:1px}
.exec-item .exec-body{flex:1}
.exec-item .exec-title{font-weight:600;margin-bottom:2px}
.exec-item .exec-detail{font-size:12px;opacity:.75}
.exec-item.critical{background:#fee2e2;border-left:4px solid #dc2626}
.exec-item.warning{background:#fef3c7;border-left:4px solid #d97706}
.exec-item.info{background:#dbeafe;border-left:4px solid #2563eb}
/* 中高剩余点击弹窗 */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:9999;justify-content:center;align-items:flex-start;padding-top:40px}
.modal-overlay.active{display:flex}
.modal-content{background:#fff;border-radius:12px;max-width:95vw;width:1200px;max-height:80vh;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.25);display:flex;flex-direction:column}
.modal-header{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #e5e7eb;background:#f8fafc;border-radius:12px 12px 0 0}
.modal-header h3{font-size:16px;color:#1a3a5c;margin:0}
.modal-close{background:none;border:none;font-size:22px;cursor:pointer;color:#6b7280;padding:4px 8px;border-radius:4px;line-height:1}
.modal-close:hover{background:#e5e7eb;color:#1f2937}
.modal-body{overflow-y:auto;padding:16px 20px;flex:1}
.modal-body .table-wrap{max-height:none;overflow:visible}
.modal-body table{font-size:11px}
.mh-remaining-link{color:#dc2626;font-weight:600;cursor:pointer;text-decoration:underline;text-decoration-style:dotted}
.mh-remaining-link:hover{color:#b91c1c}
.mh-inprogress-link{color:#2563eb;font-weight:600;cursor:pointer;text-decoration:underline;text-decoration-style:dotted}
.mh-inprogress-link:hover{color:#1d4ed8}
.bt-remaining-link{color:#dc2626;font-weight:600;cursor:pointer;text-decoration:underline;text-decoration-style:dotted}
.bt-remaining-link:hover{color:#b91c1c}
/* 可折叠子节 */
.subsection{margin:16px 0;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}
.subsection h3{font-size:15px;color:#1a3a5c;padding:12px 16px;margin:0;background:#f8fafc;cursor:pointer;display:flex;align-items:center;user-select:none;border-left:4px solid #2563eb}
.subsection h3:hover{background:#eff6ff}
.subsection h3 .arrow{display:inline-block;transition:transform .25s;margin-right:10px;font-size:12px;color:#6b7280}
.subsection h3.collapsed .arrow{transform:rotate(-90deg)}
.subsection .collapse-body{overflow:hidden;transition:max-height .35s ease}
.subsection .collapse-body.collapsed{max-height:0}
/* 可折叠主节标题 */
.section h2.collapse-toggle{cursor:pointer;display:flex;align-items:center;user-select:none}
.section h2.collapse-toggle:hover{color:#1d4ed8}
.section h2.collapse-toggle .arrow{display:inline-block;transition:transform .25s;margin-right:10px;font-size:14px;color:#6b7280;flex-shrink:0}
.section h2.collapse-toggle.collapsed .arrow{transform:rotate(-90deg)}
.section .collapse-body{overflow:hidden;transition:max-height .35s ease}
.section .collapse-body.collapsed{max-height:0}"""


# ============================================================
# HTML 生成
# ============================================================
def _format_cc(val):
    """Format cancelled count cell: badge if >0, else '0'."""
    return f'<span class="badge badge-gray">{val}</span>' if val > 0 else '0'

def _rate_badge(rate):
    """Return CSS class for a completion rate."""
    return 'badge-green' if rate >= 90 else ('badge-yellow' if rate >= 70 else 'badge-red')

def _append_subtotal_row(P, rows, label, is_grand=False, show_bt=False):
    """Compute and append a subtotal/grand-total row from a list of stats dicts."""
    if not rows:
        return
    t_all = sum(r['total'] for r in rows)
    d_all = sum(r['done'] for r in rows)
    c_all = sum(r.get('cancelled', 0) for r in rows)
    mh_t = sum(r['mh_total'] for r in rows)
    mh_c = sum(r.get('mh_cancelled', 0) for r in rows)
    mh_ip = sum(r.get('mh_in_progress', 0) for r in rows)
    mh_d = sum(r['mh_done'] for r in rows)
    mh_m = sum(r['mh_remaining'] for r in rows)
    l_t = sum(r['l_total'] for r in rows)
    l_c = sum(r.get('l_cancelled', 0) for r in rows)
    l_d = sum(r['l_done'] for r in rows)
    l_m = sum(r['l_remaining'] for r in rows)
    rate = round(d_all / (t_all - c_all) * 100, 1) if (t_all - c_all) > 0 else 0
    mh_rate = round(mh_d / (mh_t - mh_c) * 100, 1) if (mh_t - mh_c) > 0 else 0
    l_rate = round(l_d / (l_t - l_c) * 100, 1) if (l_t - l_c) > 0 else 0
    rc = _rate_badge(rate)
    mh_rc = _rate_badge(mh_rate)
    l_rc = _rate_badge(l_rate)
    border_style = 'border-top:3px double #2563eb' if is_grand else 'border-top:1px dashed #93c5fd'
    bg = '#f0f5ff' if is_grand else '#f8fafc'
    bt_cols = ''
    if show_bt:
        bt_d = sum(r.get('bt_done', 0) for r in rows)
        bt_r = sum(r.get('bt_remaining', 0) for r in rows)
        bt_t = sum(r.get('bt_total', 0) for r in rows)
        bt_rate_val = round(bt_d / bt_t * 100, 1) if bt_t > 0 else 0
        bt_rc = _rate_badge(bt_rate_val)
        bt_cols = f'<td><strong>{bt_d}</strong></td><td><span style="color:#dc2626;font-weight:700">{bt_r}</span></td><td><span class="badge {bt_rc}"><strong>{bt_rate_val}%</strong></span></td>'
    P.append(f'<tr style="font-weight:{"700" if is_grand else "600"};background:{bg};{border_style}"><td><strong>{label}</strong></td><td>-</td><td><strong>{t_all}</strong></td><td><strong>{d_all}</strong></td><td>{_format_cc(c_all)}</td><td><span class="badge {rc}"><strong>{rate}%</strong></span></td><td><strong>{mh_t}</strong></td><td>{_format_cc(mh_c)}</td><td><strong>{mh_ip}</strong></td><td><strong>{mh_d}</strong></td><td><span style="color:#dc2626;font-weight:700">{mh_m}</span></td><td><span class="badge {mh_rc}"><strong>{mh_rate}%</strong></span></td><td><strong>{l_t}</strong></td><td>{_format_cc(l_c)}</td><td><strong>{l_d}</strong></td><td><span style="color:#dc2626;font-weight:700">{l_m}</span></td><td><span class="badge {l_rc}"><strong>{l_rate}%</strong></span></td>{bt_cols}</tr>')


def _render_row(P, r, modal_idx, prefix, show_bt=False):
    """Render a single data row for a batch project matrix."""
    rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
    mh_rc = 'badge-green' if r['mh_rate'] >= 90 else ('badge-yellow' if r['mh_rate'] >= 70 else 'badge-red')
    l_rc = 'badge-green' if r['l_rate'] >= 90 else ('badge-yellow' if r['l_rate'] >= 70 else 'badge-red')
    sc = 'badge-purple' if r['system'] == 'JAVA-专业系统' else 'badge-blue'
    cc = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
    mh_cc_str = f'<span class="badge badge-gray">{r["mh_cancelled"]}</span>' if r.get('mh_cancelled', 0) > 0 else '0'
    l_cc_str = f'<span class="badge badge-gray">{r["l_cancelled"]}</span>' if r.get('l_cancelled', 0) > 0 else '0'
    if r.get('mh_remaining_tasks') and len(r['mh_remaining_tasks']) > 0:
        modal_id = f'{prefix}_mh_modal_{modal_idx}'
        mh_cell = f'<td><span class="mh-remaining-link" onclick="openModal(\'{modal_id}\')">{r["mh_remaining"]}</span></td>'
    else:
        modal_id = None
        mh_cell = f'<td><span style="color:#6b7280">{r["mh_remaining"]}</span></td>'
    # 中高进行中 — clickable if tasks exist
    mh_ip = r.get('mh_in_progress', 0)
    if r.get('mh_in_progress_tasks') and len(r['mh_in_progress_tasks']) > 0:
        mh_ip_modal_id = f'{prefix}_mhip_modal_{modal_idx}'
        mh_ip_cell = f'<td><span class="mh-inprogress-link" onclick="openModal(\'{mh_ip_modal_id}\')">{mh_ip}</span></td>'
    else:
        mh_ip_modal_id = None
        mh_ip_cell = f'<td><span style="color:#6b7280">{mh_ip}</span></td>'
    if show_bt:
        bt_rate_val = r.get('bt_rate', 0)
        bt_rc = 'badge-green' if bt_rate_val >= 90 else ('badge-yellow' if bt_rate_val >= 70 else 'badge-red')
        if r.get('bt_remaining_tasks') and len(r['bt_remaining_tasks']) > 0:
            bt_modal_id = f'{prefix}_bt_modal_{modal_idx}'
            bt_cell = f'<td><span class="bt-remaining-link" onclick="openModal(\'{bt_modal_id}\')">{r["bt_remaining"]}</span></td>'
        else:
            bt_modal_id = None
            bt_cell = f'<td><span style="color:#6b7280">{r["bt_remaining"]}</span></td>'
        bt_cols = f'<td>{r["bt_done"]}</td>{bt_cell}<td><span class="badge {bt_rc}">{bt_rate_val}%</span></td>'
    else:
        bt_cols = ''
        bt_modal_id = None
    P.append(f'<tr><td><span class="badge {sc}">{r["system"]}</span></td><td style="text-align:left;font-weight:500">{r["project"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["mh_total"]}</td><td>{mh_cc_str}</td>{mh_ip_cell}<td>{r["mh_done"]}</td>{mh_cell}<td><span class="badge {mh_rc}">{r["mh_rate"]}%</span></td><td>{r["l_total"]}</td><td>{l_cc_str}</td><td>{r["l_done"]}</td><td><span style="color:#dc2626;font-weight:600">{r["l_remaining"]}</span></td><td><span class="badge {l_rc}">{r["l_rate"]}%</span></td>{bt_cols}</tr>')

def _render_modals(P, bp, prefix):
    """Render modal popups for a batch project matrix (MH remaining + MH in-progress)."""
    mi = 0
    for r in bp:
        # --- MH remaining modals ---
        tasks = r.get('mh_remaining_tasks', [])
        if tasks:
            modal_id = f'{prefix}_mh_modal_{mi}'
            P.append(f'<div class="modal-overlay" id="{modal_id}" onclick="if(event.target===this)closeModal(\'{modal_id}\')">')
            P.append(f'<div class="modal-content">')
            P.append(f'<div class="modal-header"><h3>📋 {r["system"]} · {r["project"]} — 中高优先级剩余任务（{len(tasks)}条）</h3><button class="modal-close" onclick="closeModal(\'{modal_id}\')">&times;</button></div>')
            P.append(f'<div class="modal-body"><div class="table-wrap"><table>')
            P.append('<tr><th>#</th><th>项目</th><th>任务</th><th>模块</th><th>优先级</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th><th>延期原因</th></tr>')
            for ti, t in enumerate(tasks, 1):
                pc = 'badge-red' if t['priority'] == '高' else 'badge-yellow'
                fs_cls = 'badge-green' if t['fs_status'] == '已完成' else ('badge-yellow' if t['fs_status'] == '进行中' else ('badge-red' if t['fs_status'] == '待处理' else 'badge-gray'))
                bt_cls = 'badge-green' if t['bt_status'] == '已完成' else ('badge-yellow' if t['bt_status'] == '进行中' else ('badge-red' if t['bt_status'] == '待处理' else 'badge-gray'))
                ts_cls = 'badge-green' if t['ts_status'] == '已完成' else ('badge-yellow' if t['ts_status'] == '进行中' else ('badge-red' if t['ts_status'] == '待处理' else 'badge-gray'))
                reason = t.get('reason', '') if t.get('reason', '') else '-'
                P.append(f'<tr><td>{ti}</td><td style="text-align:left">{t["project"]}</td><td style="text-align:left;max-width:180px">{t["task"]}</td><td>{t["module"]}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["status"]}</td><td>{t["person"]}</td><td>{t["end"]}</td><td>{t["progress"]}</td><td><span class="badge {fs_cls}">{t["fs_status"]}</span></td><td><span class="badge {bt_cls}">{t["bt_status"]}</span></td><td><span class="badge {ts_cls}">{t["ts_status"]}</span></td><td style="text-align:left;font-size:11px">{reason}</td></tr>')
            P.append('</table></div></div></div></div>')
        # --- MH in-progress modals ---
        ip_tasks = r.get('mh_in_progress_tasks', [])
        if ip_tasks:
            ip_modal_id = f'{prefix}_mhip_modal_{mi}'
            P.append(f'<div class="modal-overlay" id="{ip_modal_id}" onclick="if(event.target===this)closeModal(\'{ip_modal_id}\')">')
            P.append(f'<div class="modal-content">')
            P.append(f'<div class="modal-header"><h3>🔄 {r["system"]} · {r["project"]} — 中高优先级进行中任务（{len(ip_tasks)}条）</h3><button class="modal-close" onclick="closeModal(\'{ip_modal_id}\')">&times;</button></div>')
            P.append(f'<div class="modal-body"><div class="table-wrap"><table>')
            P.append('<tr><th>#</th><th>项目</th><th>任务</th><th>模块</th><th>优先级</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th><th>延期原因</th></tr>')
            for ti, t in enumerate(ip_tasks, 1):
                pc = 'badge-red' if t['priority'] == '高' else 'badge-yellow'
                fs_cls = 'badge-green' if t['fs_status'] == '已完成' else ('badge-yellow' if t['fs_status'] == '进行中' else ('badge-red' if t['fs_status'] == '待处理' else 'badge-gray'))
                bt_cls = 'badge-green' if t['bt_status'] == '已完成' else ('badge-yellow' if t['bt_status'] == '进行中' else ('badge-red' if t['bt_status'] == '待处理' else 'badge-gray'))
                ts_cls = 'badge-green' if t['ts_status'] == '已完成' else ('badge-yellow' if t['ts_status'] == '进行中' else ('badge-red' if t['ts_status'] == '待处理' else 'badge-gray'))
                reason = t.get('reason', '') if t.get('reason', '') else '-'
                P.append(f'<tr><td>{ti}</td><td style="text-align:left">{t["project"]}</td><td style="text-align:left;max-width:180px">{t["task"]}</td><td>{t["module"]}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["status"]}</td><td>{t["person"]}</td><td>{t["end"]}</td><td>{t["progress"]}</td><td><span class="badge {fs_cls}">{t["fs_status"]}</span></td><td><span class="badge {bt_cls}">{t["bt_status"]}</span></td><td><span class="badge {ts_cls}">{t["ts_status"]}</span></td><td style="text-align:left;font-size:11px">{reason}</td></tr>')
            P.append('</table></div></div></div></div>')
        mi += 1

def _render_batch_matrix(P, bp, batch_label, batch_letter, show_bt=False, subsection_num=None):
    """Render a full batch project matrix with inline SAP/JAVA subtotals and modals."""
    if not bp:
        return
    if subsection_num:
        P.append(f'<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>{subsection_num} {batch_label} · 系统类型 × 项目 — 完成进度</h3>')
        P.append(f'<div class="collapse-body collapsed">')
    else:
        P.append(f'<div class="section"><h2>一、{batch_label} · 系统类型 × 项目 — 完成进度</h2>')
    P.append(f'<div class="alert alert-info">{batch_label}按<span style="font-weight:600;color:#1d4ed8">系统类型</span>×<span style="font-weight:600;color:#059669">项目</span>下钻视图，按完成率升序排列。</div>')
    P.append('<div class="table-wrap"><table>')
    bt_header = '<th>测试已完成</th><th>测试剩余</th><th>测试完成率</th>' if show_bt else ''
    P.append(f'<tr><th>系统类型</th><th>项目</th><th>总任务</th><th>已完成</th><th>已取消</th><th>整体完成率</th><th>中高总数</th><th>中高已取消</th><th>中高进行中</th><th>中高已完成</th><th>中高剩余</th><th>中高完成率</th><th>低总数</th><th>低已取消</th><th>低已完成</th><th>低剩余</th><th>低完成率</th>{bt_header}</tr>')

    sap_rows = [r for r in bp if r['system'] == 'SAP']
    java_rows = [r for r in bp if r['system'] == 'JAVA-专业系统']
    prefix = batch_letter.lower()

    # Render SAP rows then SAP subtotal inline
    modal_idx = 0
    for r in sap_rows:
        _render_row(P, r, modal_idx, prefix, show_bt)
        modal_idx += 1
    _append_subtotal_row(P, sap_rows, '📊 SAP 小计', show_bt=show_bt)

    # Render JAVA rows then JAVA subtotal inline
    for r in java_rows:
        _render_row(P, r, modal_idx, prefix, show_bt)
        modal_idx += 1
    _append_subtotal_row(P, java_rows, '📊 JAVA 小计', show_bt=show_bt)

    # Grand total
    _append_subtotal_row(P, bp, '📊 合计', is_grand=True, show_bt=show_bt)
    P.append('</table></div>')

    # Modals (MH)
    _render_modals(P, bp, prefix)
    # BT Modals (only for C-batch)
    if show_bt:
        bt_mi = 0
        for r in bp:
            bt_tasks = r.get('bt_remaining_tasks', [])
            if not bt_tasks:
                bt_mi += 1
                continue
            bt_modal_id = f'{prefix}_bt_modal_{bt_mi}'
            P.append(f'<div class="modal-overlay" id="{bt_modal_id}" onclick="if(event.target===this)closeModal(\'{bt_modal_id}\')">')
            P.append(f'<div class="modal-content">')
            P.append(f'<div class="modal-header"><h3>🧪 {r["system"]} · {r["project"]} — 业务测试剩余任务（{len(bt_tasks)}条）</h3><button class="modal-close" onclick="closeModal(\'{bt_modal_id}\')">&times;</button></div>')
            P.append(f'<div class="modal-body"><div class="table-wrap"><table>')
            P.append('<tr><th>#</th><th>项目</th><th>任务</th><th>模块</th><th>优先级</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>业务测试状态</th><th>业务测试负责人</th><th>延期原因</th></tr>')
            for ti, t in enumerate(bt_tasks, 1):
                pc = 'badge-red' if t['priority'] == '高' else 'badge-yellow'
                bt_cls = 'badge-green' if t['bt_status'] == '已完成' else ('badge-yellow' if t['bt_status'] == '进行中' else ('badge-red' if t['bt_status'] == '待处理' else 'badge-gray'))
                reason = t.get('reason', '') if t.get('reason', '') else '-'
                P.append(f'<tr><td>{ti}</td><td style="text-align:left">{t["project"]}</td><td style="text-align:left;max-width:180px">{t["task"]}</td><td>{t["module"]}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["status"]}</td><td>{t["person"]}</td><td>{t["end"]}</td><td>{t["progress"]}</td><td><span class="badge {bt_cls}">{t["bt_status"]}</span></td><td>{t["bt_person"]}</td><td style="text-align:left;font-size:11px">{reason}</td></tr>')
            P.append('</table></div></div></div></div>')
            bt_mi += 1
    if subsection_num:
        P.append('</div></div>')  # close collapse-body and subsection
    else:
        P.append('</div>')


def generate_html(d, output_path):
    P = []  # parts

    # ===== 构建质量维度查找映射（供各章节交叉引用） =====
    proj_quality_map = {}
    bs_quality_map = {}
    team_quality_map = {}
    module_quality_map = {}
    if d.get('quality'):
        q = d['quality']
        is_rich = 'summary' in q
        if is_rich and q.get('by_project'):
            for pq in q['by_project']:
                proj_quality_map[pq['project']] = pq['total']
        if is_rich and q.get('by_batch_system'):
            for bsq in q['by_batch_system']:
                bs_quality_map[(bsq['batch'], bsq['system'])] = bsq['total']
        if is_rich and q.get('by_team'):
            for tq in q['by_team']:
                team_quality_map[(tq['team'], tq['batch'], tq['system'])] = tq['total']
        if is_rich and q.get('by_module'):
            for mq in q['by_module']:
                module_quality_map[(mq['module'], mq['batch'], mq['system'])] = mq['total']

    P.append('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">')
    P.append('<title>1455项目 PMO监控分析报告</title>')
    P.append('<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>')
    P.append('<style>' + CSS + '</style>\n</head>\n<body>')
    P.append('<div class="header"><h1>1455项目 — PMO项目监控分析报告</h1>')
    P.append(f'<div class="sub">数据截止: {d["report_date"]} | 报告生成: {d["generated_at"]} | A/B/C批次 | JAVA-专业系统 / SAP</div></div>')
    P.append('<div class="container">')

    # ===== 执行摘要（报告最顶部，管理者30秒掌握全局） =====
    exec_items = d.get('executive_summary', [])
    if exec_items:
        has_critical = any(it['level'] == 'critical' for it in exec_items)
        summary_bg = '#fef2f2' if has_critical else '#fffbeb'
        summary_border = '#dc2626' if has_critical else '#d97706'
        P.append(f'<div class="exec-summary" style="background:{summary_bg};border-left:4px solid {summary_border}">')
        P.append('<h2>📋 执行摘要 — 本周关键发现</h2>')
        for it in exec_items:
            P.append(f'<div class="exec-item {it["level"]}"><span class="exec-icon">{it["icon"]}</span><div class="exec-body"><div class="exec-title">{it["title"]}</div>')
            if it.get('detail'):
                P.append(f'<div class="exec-detail">{it["detail"]}</div>')
            P.append('</div></div>')
        P.append('</div>')

    # ===== KPI =====
    k = d['kpi']
    P.append('<div class="kpi-grid">')
    for label, val, cls in [
        ('总任务数', k['total'], 'blue'), ('已完成', k['done'], 'green'),
        ('完成率', f"{k['comp_rate']}%", 'green'), ('未完成', k['undone'], 'orange'),
        ('已取消', k.get('cancelled', 0), 'gray'),
        ('总人天', str(k['total_days']), 'blue'), ('⚠️ 逾期', str(k['overdue']), 'red'),
        ('⏰ 临期预警', str(k['near_due']), 'purple'), ('项目标段', str(k['projects']), 'gray'),
    ]:
        P.append(f'<div class="kpi-card {cls}"><div class="label">{label}</div><div class="value">{val}</div></div>')
    # 数据质量 KPI（作为整体维度指标）
    if d.get('quality'):
        qd = d['quality']
        total_issues = qd.get('total_issues', 0)
        q_cls = 'green' if total_issues == 0 else 'red'
        P.append(f'<div class="kpi-card {q_cls}"><div class="label">📋 数据质量问题</div><div class="value">{total_issues}</div></div>')
    P.append('</div>')

    # ===================================================================
    # 板块一：系统×批次完成进度
    # ===================================================================

    # ===== 一、SAP / 专业系统 × 批次 — 完成进度（含中高优先级） =====
    sbp = d.get('sys_batch_priority', [])
    P.append(f'<div class="section"><h2>1 SAP / 专业系统 × 批次 — 完成进度（含中高优先级）</h2>')
    P.append('<div class="alert alert-info">按 SAP / 专业系统 & 批次交叉统计整体完成率，并单独标注<span style="font-weight:600;color:#dc2626">中高优先级（高+中）</span>任务的完成进度。中高优先级完成率为项目关键路径指标。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>系统类型</th><th>批次</th><th>总任务</th><th>已完成</th><th>已取消</th><th>整体完成率</th><th>中高优先级总数</th><th>中高已取消</th><th>中高已完成</th><th>中高剩余</th><th>中高完成率</th><th>低优先级总数</th><th>低已取消</th><th>低已完成</th><th>低剩余</th><th>低完成率</th><th>人天</th></tr>')
    for idx, r in enumerate(sbp):
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
        mh_rc = 'badge-green' if r['mh_rate'] >= 90 else ('badge-yellow' if r['mh_rate'] >= 70 else 'badge-red')
        l_rc = 'badge-green' if r['l_rate'] >= 90 else ('badge-yellow' if r['l_rate'] >= 70 else 'badge-red')
        sc = 'badge-purple' if r['system'] == 'JAVA-专业系统' else 'badge-blue'
        cc = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
        rows_with_tasks = [i for i, rr in enumerate(sbp) if rr.get('mh_remaining_tasks') and len(rr['mh_remaining_tasks']) > 0]
        modal_id = f'mh_modal_{idx}'
        if r.get('mh_remaining_tasks') and len(r['mh_remaining_tasks']) > 0:
            mh_cell = f'<td><span class="mh-remaining-link" onclick="openModal(\'{modal_id}\')">{r["mh_remaining"]}</span></td>'
        else:
            mh_cell = f'<td><span style="color:#6b7280">{r["mh_remaining"]}</span></td>'
        mh_cc_str = f'<span class="badge badge-gray">{r["mh_cancelled"]}</span>' if r.get('mh_cancelled', 0) > 0 else '0'
        l_cc_str = f'<span class="badge badge-gray">{r["l_cancelled"]}</span>' if r.get('l_cancelled', 0) > 0 else '0'
        P.append(f'<tr><td><span class="badge {sc}">{r["system"]}</span></td><td><strong>{r["batch"]}</strong></td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["mh_total"]}</td><td>{mh_cc_str}</td><td>{r["mh_done"]}</td>{mh_cell}<td><span class="badge {mh_rc}">{r["mh_rate"]}%</span></td><td>{r["l_total"]}</td><td>{l_cc_str}</td><td>{r["l_done"]}</td><td><span style="color:#dc2626;font-weight:600">{r["l_remaining"]}</span></td><td><span class="badge {l_rc}">{r["l_rate"]}%</span></td><td>{r["days"]}</td></tr>')
    # 整体汇总行
    if sbp:
        total_all = sum(r['total'] for r in sbp)
        done_all = sum(r['done'] for r in sbp)
        cancelled_all = sum(r.get('cancelled', 0) for r in sbp)
        mh_total_all = sum(r['mh_total'] for r in sbp)
        mh_cancelled_all = sum(r.get('mh_cancelled', 0) for r in sbp)
        mh_done_all = sum(r['mh_done'] for r in sbp)
        mh_remaining_all = sum(r['mh_remaining'] for r in sbp)
        l_total_all = sum(r['l_total'] for r in sbp)
        l_cancelled_all = sum(r.get('l_cancelled', 0) for r in sbp)
        l_done_all = sum(r['l_done'] for r in sbp)
        l_remaining_all = sum(r['l_remaining'] for r in sbp)
        days_all = sum(r['days'] for r in sbp)
        rate_all = round(done_all / (total_all - cancelled_all) * 100, 1) if (total_all - cancelled_all) > 0 else 0
        mh_rate_all = round(mh_done_all / (mh_total_all - mh_cancelled_all) * 100, 1) if (mh_total_all - mh_cancelled_all) > 0 else 0
        l_rate_all = round(l_done_all / (l_total_all - l_cancelled_all) * 100, 1) if (l_total_all - l_cancelled_all) > 0 else 0
        rc_all = 'badge-green' if rate_all >= 90 else ('badge-yellow' if rate_all >= 70 else 'badge-red')
        mh_rc_all = 'badge-green' if mh_rate_all >= 90 else ('badge-yellow' if mh_rate_all >= 70 else 'badge-red')
        l_rc_all = 'badge-green' if l_rate_all >= 90 else ('badge-yellow' if l_rate_all >= 70 else 'badge-red')
        cc_all = f'<span class="badge badge-gray">{cancelled_all}</span>' if cancelled_all > 0 else '0'
        mh_cc_all = f'<span class="badge badge-gray">{mh_cancelled_all}</span>' if mh_cancelled_all > 0 else '0'
        l_cc_all = f'<span class="badge badge-gray">{l_cancelled_all}</span>' if l_cancelled_all > 0 else '0'
        P.append(f'<tr style="font-weight:700;background:#f0f5ff;border-top:2px solid #2563eb"><td><strong>📊 合计</strong></td><td>-</td><td><strong>{total_all}</strong></td><td><strong>{done_all}</strong></td><td>{cc_all}</td><td><span class="badge {rc_all}"><strong>{rate_all}%</strong></span></td><td><strong>{mh_total_all}</strong></td><td>{mh_cc_all}</td><td><strong>{mh_done_all}</strong></td><td><span style="color:#dc2626;font-weight:700">{mh_remaining_all}</span></td><td><span class="badge {mh_rc_all}"><strong>{mh_rate_all}%</strong></span></td><td><strong>{l_total_all}</strong></td><td>{l_cc_all}</td><td><strong>{l_done_all}</strong></td><td><span style="color:#dc2626;font-weight:700">{l_remaining_all}</span></td><td><span class="badge {l_rc_all}"><strong>{l_rate_all}%</strong></span></td><td><strong>{days_all}</strong></td></tr>')
    P.append('</table></div>')
    # 中高剩余弹窗
    for idx, r in enumerate(sbp):
        tasks = r.get('mh_remaining_tasks', [])
        if not tasks:
            continue
        modal_id = f'mh_modal_{idx}'
        P.append(f'<div class="modal-overlay" id="{modal_id}" onclick="if(event.target===this)closeModal(\'{modal_id}\')">')
        P.append(f'<div class="modal-content">')
        P.append(f'<div class="modal-header"><h3>📋 {r["system"]} · {r["batch"]} — 中高优先级剩余任务（{len(tasks)}条）</h3><button class="modal-close" onclick="closeModal(\'{modal_id}\')">&times;</button></div>')
        P.append(f'<div class="modal-body"><div class="table-wrap"><table>')
        P.append('<tr><th>#</th><th>项目</th><th>任务</th><th>模块</th><th>优先级</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th><th>延期原因</th></tr>')
        for ti, t in enumerate(tasks, 1):
            pc = 'badge-red' if t['priority'] == '高' else 'badge-yellow'
            fs_cls = 'badge-green' if t['fs_status'] == '已完成' else ('badge-yellow' if t['fs_status'] == '进行中' else ('badge-red' if t['fs_status'] == '待处理' else 'badge-gray'))
            bt_cls = 'badge-green' if t['bt_status'] == '已完成' else ('badge-yellow' if t['bt_status'] == '进行中' else ('badge-red' if t['bt_status'] == '待处理' else 'badge-gray'))
            ts_cls = 'badge-green' if t['ts_status'] == '已完成' else ('badge-yellow' if t['ts_status'] == '进行中' else ('badge-red' if t['ts_status'] == '待处理' else 'badge-gray'))
            reason = t.get('reason', '') if t.get('reason', '') else '-'
            P.append(f'<tr><td>{ti}</td><td style="text-align:left">{t["project"]}</td><td style="text-align:left;max-width:180px">{t["task"]}</td><td>{t["module"]}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["status"]}</td><td>{t["person"]}</td><td>{t["end"]}</td><td>{t["progress"]}</td><td><span class="badge {fs_cls}">{t["fs_status"]}</span></td><td><span class="badge {bt_cls}">{t["bt_status"]}</span></td><td><span class="badge {ts_cls}">{t["ts_status"]}</span></td><td style="text-align:left;font-size:11px">{reason}</td></tr>')
        P.append('</table></div></div></div></div>')
    # ===== 1.1 / 1.2 / 1.3 批次 · 系统类型 × 项目 — 完成进度 =====
    _render_batch_matrix(P, d.get('a_batch_project_priority', []), 'A批次', 'A', subsection_num='1.1')
    _render_batch_matrix(P, d.get('b_batch_project_priority', []), 'B批次', 'B', subsection_num='1.2')
    _render_batch_matrix(P, d.get('c_batch_project_priority', []), 'C批次', 'C', show_bt=True, subsection_num='1.3')
    P.append('</div>')

    # ===================================================================
    # 板块二：逾期 & 临期（开发 + 业务测试）
    # ===================================================================

    # ===== 2 逾期 & 临期 — 延期原因与备注 =====
    overdue_items = [(item, '🔴逾期') for item in d['overdue_list']]
    near_items = [(item, '🟡临期') for item in d['near_due_list']]
    overdue_items.sort(key=lambda x: -x[0].get('days_diff', 0))
    near_items.sort(key=lambda x: x[0].get('days_diff', 0))
    all_risk = overdue_items + near_items
    bt_overdue_items = [(item, '🔴逾期') for item in d.get('bt_overdue_list', [])]
    bt_near_items = [(item, '🟡临期') for item in d.get('bt_near_due_list', [])]
    bt_overdue_items.sort(key=lambda x: -x[0].get('days_diff', 0))
    bt_near_items.sort(key=lambda x: x[0].get('days_diff', 0))
    bt_all_risk = bt_overdue_items + bt_near_items

    P.append(f'<div class="section" style="border-left:4px solid #dc2626">')
    P.append(f'<h2>2 逾期 & 临期 — 延期原因与备注</h2>')
    P.append('<div class="alert alert-danger">按开发（任务计划结束日期）和业务测试（业务测试计划结束日期）两个维度分别统计逾期+临期任务。重点关注：延期原因是否已填写、备注是否有说明。</div>')

    # ----- 2.1 开发逾期 & 临期 -----
    P.append('<div class="subsection">')
    P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.1 逾期 & 临期任务 — 开发（{len(all_risk)}条）</h3>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>类型</th><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>状态</th><th>FS状态</th><th>业务测试状态</th><th>TS状态</th><th>优先级</th><th>负责人</th><th>计划结束</th><th>进度</th><th>延期原因</th><th>备注</th></tr>')
    for item, tag in all_risk:
        reason = item.get('reason', '（未填写）')
        remark = item.get('remark', '（无备注）')
        reason_cls = 'color:#dc2626;font-weight:600' if reason == '（未填写）' else ''
        remark_cls = 'color:#9ca3af' if remark == '（无备注）' else ''
        diff = item.get('days_diff', 0)
        diff_str = f'+{diff}天' if item.get('tag') == '逾期' else f'{diff}天'
        pc = 'badge-red' if item['priority'] == '高' else ('badge-yellow' if item['priority'] == '中' else 'badge-gray')
        fs = item.get('fs_status', '-')
        bt = item.get('bt_status', '-')
        ts = item.get('ts_status', '-')
        fs_cls = 'badge-green' if fs == '已完成' else ('badge-yellow' if fs == '进行中' else ('badge-red' if fs == '待处理' else 'badge-gray'))
        bt_cls = 'badge-green' if bt == '已完成' else ('badge-yellow' if bt == '进行中' else ('badge-red' if bt == '待处理' else 'badge-gray'))
        ts_cls = 'badge-green' if ts == '已完成' else ('badge-yellow' if ts == '进行中' else ('badge-red' if ts == '待处理' else 'badge-gray'))
        P.append(f'<tr><td>{tag}</td><td style="text-align:left">{item["project"]}</td><td>{item["batch"]}</td><td>{item["system"]}</td><td>{item["module"]}</td><td style="text-align:left;max-width:200px">{item["task"]}</td><td>{item["status"]}</td><td><span class="badge {fs_cls}">{fs}</span></td><td><span class="badge {bt_cls}">{bt}</span></td><td><span class="badge {ts_cls}">{ts}</span></td><td><span class="badge {pc}">{item["priority"]}</span></td><td>{item["person"]}</td><td>{item["end"]} ({diff_str})</td><td>{item["progress"]}</td><td style="text-align:left;font-size:11px;{reason_cls}">{reason}</td><td style="text-align:left;font-size:11px;{remark_cls}">{remark}</td></tr>')
    P.append('</table></div>')
    # 分布摘要 — 开发
    dev_proj_c = Counter(item['project'] for item, _ in all_risk)
    dev_batch_c = Counter(item['batch'] for item, _ in all_risk)
    dev_sys_c = Counter(item['system'] for item, _ in all_risk)
    dev_reason_ok = sum(1 for item, _ in all_risk if item.get('reason', '（未填写）') not in ['（未填写）', '-', ''])
    dev_remark_ok = sum(1 for item, _ in all_risk if item.get('remark', '（无备注）') not in ['（无备注）', '-', ''])
    P.append('<div style="margin-top:10px;font-size:13px;color:#666">')
    P.append(f'📌 涉及项目: {", ".join(f"{k}({v})" for k, v in dev_proj_c.most_common())} | ')
    P.append(f'批次: {", ".join(f"{k}({v})" for k, v in dev_batch_c.most_common())} | ')
    P.append(f'系统: {", ".join(f"{k}({v})" for k, v in dev_sys_c.most_common())} | ')
    P.append(f'延期原因填写率: {dev_reason_ok}/{len(all_risk)} | 备注填写率: {dev_remark_ok}/{len(all_risk)}')
    P.append('</div>')
    P.append('</div></div>')  # close collapse-body & subsection

    # ----- 2.2 业务测试逾期 & 临期 -----
    P.append('<div class="subsection">')
    P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.2 逾期 & 临期任务 — 测试（{len(bt_all_risk)}条）</h3>')
    P.append('<div class="collapse-body collapsed">')
    if bt_all_risk:
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>类型</th><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>状态</th><th>业务测试状态</th><th>业务测试负责人</th><th>优先级</th><th>负责人</th><th>测试计划结束</th><th>延期原因</th><th>备注</th></tr>')
        for item, tag in bt_all_risk:
            reason = item.get('reason', '（未填写）')
            remark = item.get('remark', '（无备注）')
            reason_cls = 'color:#dc2626;font-weight:600' if reason == '（未填写）' else ''
            remark_cls = 'color:#9ca3af' if remark == '（无备注）' else ''
            diff = item.get('days_diff', 0)
            diff_str = f'+{diff}天' if item.get('tag') == '逾期' else f'{diff}天'
            pc = 'badge-red' if item['priority'] == '高' else ('badge-yellow' if item['priority'] == '中' else 'badge-gray')
            bt = item.get('bt_status', '-')
            bt_cls = 'badge-green' if bt == '已完成' else ('badge-yellow' if bt == '进行中' else ('badge-red' if bt == '待处理' else 'badge-gray'))
            bt_person = item.get('bt_person', '-')
            P.append(f'<tr><td>{tag}</td><td style="text-align:left">{item["project"]}</td><td>{item["batch"]}</td><td>{item["system"]}</td><td>{item["module"]}</td><td style="text-align:left;max-width:200px">{item["task"]}</td><td>{item["status"]}</td><td><span class="badge {bt_cls}">{bt}</span></td><td>{bt_person}</td><td><span class="badge {pc}">{item["priority"]}</span></td><td>{item["person"]}</td><td>{item["end"]} ({diff_str})</td><td style="text-align:left;font-size:11px;{reason_cls}">{reason}</td><td style="text-align:left;font-size:11px;{remark_cls}">{remark}</td></tr>')
        P.append('</table></div>')
        # 分布摘要 — 测试
        bt_proj_c = Counter(item['project'] for item, _ in bt_all_risk)
        bt_batch_c = Counter(item['batch'] for item, _ in bt_all_risk)
        bt_sys_c = Counter(item['system'] for item, _ in bt_all_risk)
        bt_reason_ok = sum(1 for item, _ in bt_all_risk if item.get('reason', '（未填写）') not in ['（未填写）', '-', ''])
        bt_remark_ok = sum(1 for item, _ in bt_all_risk if item.get('remark', '（无备注）') not in ['（无备注）', '-', ''])
        P.append('<div style="margin-top:10px;font-size:13px;color:#666">')
        P.append(f'📌 涉及项目: {", ".join(f"{k}({v})" for k, v in bt_proj_c.most_common())} | ')
        P.append(f'批次: {", ".join(f"{k}({v})" for k, v in bt_batch_c.most_common())} | ')
        P.append(f'系统: {", ".join(f"{k}({v})" for k, v in bt_sys_c.most_common())} | ')
        P.append(f'延期原因填写率: {bt_reason_ok}/{len(bt_all_risk)} | 备注填写率: {bt_remark_ok}/{len(bt_all_risk)}')
        P.append('</div>')
    else:
        P.append('<div class="alert alert-success">✅ 当前没有业务测试逾期的任务。</div>')
    P.append('</div></div>')  # close collapse-body & subsection

    P.append('</div>')  # close section

    # ===================================================================
    # 板块三：进度（三 ~ 八）
    # ===================================================================

    # ===== 三、项目完成率排名 =====
    P.append('<div class="section">')
    P.append('<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>3 项目标段完成率排名（批次 × 系统类型）</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>排名</th><th>项目标段</th><th>批次</th><th>系统类型</th><th>总任务</th><th>已完成</th><th>已取消</th><th>完成率</th><th>人天</th><th>逾期</th><th>临期</th><th>质量问题</th></tr>')
    for i, r in enumerate(d['proj_ranking']):
        rc = 'badge-green' if r['rate'] >= 90 else ('badge-yellow' if r['rate'] >= 70 else 'badge-red')
        bc = 'badge-blue' if r['batch'] != '未标注批次' else 'badge-gray'
        sc = 'badge-purple' if r['system'] == 'JAVA-专业系统' else 'badge-blue'
        od_str = f'<span class="badge badge-red">{r["overdue"]}</span>' if r['overdue'] > 0 else '-'
        nd_str = f'<span class="badge badge-yellow">{r["near_due"]}</span>' if r['near_due'] > 0 else '-'
        # 质量问题交叉引用
        q_issues = proj_quality_map.get(r['project'], 0)
        q_str = f'<span class="badge badge-red">{q_issues}</span>' if q_issues > 100 else (f'<span class="badge badge-yellow">{q_issues}</span>' if q_issues > 0 else '<span class="badge badge-green">0</span>')
        cc_str = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
        P.append(f'<tr><td>{i + 1}</td><td style="text-align:left;font-weight:600">{r["project"]}</td><td><span class="badge {bc}">{r["batch"]}</span></td><td><span class="badge {sc}">{r["system"]}</span></td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc_str}</td><td><span class="badge {rc}">{r["rate"]}%</span></td><td>{r["days"]}</td><td>{od_str}</td><td>{nd_str}</td><td>{q_str}</td></tr>')
    P.append('</table></div></div></div>')

    # ===== 四、批次 × 系统类型 总览 =====
    P.append('<div class="section">')
    P.append('<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>4 批次 × 系统类型 总览</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="chart-row"><div class="chart-box"><h3>各批次任务分布</h3><canvas id="batchBarChart"></canvas></div>')
    P.append('<div class="chart-box"><h3>系统类型分布</h3><canvas id="sysPieChart"></canvas></div></div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>系统类型</th><th>总任务</th><th>已完成</th><th>已取消</th><th>未完成</th><th>完成率</th><th>人天</th><th>质量问题</th></tr>')
    for r in d['batch_system']:
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
        # 质量问题交叉引用
        q_issues = bs_quality_map.get((r['batch'], r['system']), 0)
        q_str = f'<span class="badge badge-red">{q_issues}</span>' if q_issues > 500 else (f'<span class="badge badge-yellow">{q_issues}</span>' if q_issues > 0 else '<span class="badge badge-green">0</span>')
        cc_str = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc_str}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td><td>{q_str}</td></tr>')
    P.append('</table></div></div></div>')

    # ===== 五、未完成任务明细 =====
    undone = d['undone_detail']
    cancelled = d.get('cancelled_detail', [])
    P.append(f'<div class="section" style="border-left:4px solid #dc2626">')
    P.append(f'<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>5 未完成任务明细（{len(undone)}条）— 项目 × 批次 × 系统类型</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="alert alert-info">以下仅包含状态为「未完成」的任务（不含已取消），完成率 = 已完成 / (总任务 - 已取消)。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务名称</th><th>类型</th><th>优先级</th><th>状态</th><th>负责人</th><th>进度</th></tr>')
    for r in undone:
        pc = 'badge-red' if r['priority'] == '高' else ('badge-yellow' if r['priority'] == '中' else 'badge-gray')
        P.append(f'<tr><td style="text-align:left">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["module"]}</td><td style="text-align:left;max-width:250px">{r["task"]}</td><td>{r["type"]}</td><td><span class="badge {pc}">{r["priority"]}</span></td><td>{r["status"]}</td><td>{r["person"]}</td><td>{r["progress"]}</td></tr>')
    P.append('</table></div>')
    # 已取消任务明细
    if cancelled:
        P.append(f'<h3 style="margin-top:20px">📌 已取消任务明细（{len(cancelled)}条）— 不计入完成率分母</h3>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务名称</th><th>类型</th><th>优先级</th><th>状态</th><th>负责人</th><th>进度</th></tr>')
        for r in cancelled:
            pc = 'badge-red' if r['priority'] == '高' else ('badge-yellow' if r['priority'] == '中' else 'badge-gray')
            P.append(f'<tr><td style="text-align:left">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["module"]}</td><td style="text-align:left;max-width:250px">{r["task"]}</td><td>{r["type"]}</td><td><span class="badge {pc}">{r["priority"]}</span></td><td>{r["status"]}</td><td>{r["person"]}</td><td>{r["progress"]}</td></tr>')
        P.append('</table></div>')
    P.append('</div></div>')

    # ===== 六、阶段卡点分析 =====
    P.append('<div class="section">')
    P.append('<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>6 任务阶段卡点分析</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="alert alert-info">FS / 业务测试 / TS 三阶段状态分布。「卡点」= 该阶段状态为"待处理"或"进行中"的任务，表示任务在此阶段受阻，需推动。</div>')

    # 6.1 各阶段状态分布
    blockage = d.get('phase_blockage', [])
    if blockage:
        P.append('<h3>6.1 各阶段状态分布</h3>')
        P.append('<div class="chart-row"><div class="chart-box" style="grid-column:1/-1"><h3>阶段状态堆叠图（待处理/进行中/已完成/不适用）</h3><canvas id="phaseBlockageChart"></canvas></div></div>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>阶段</th><th>待处理</th><th>进行中</th><th>已完成</th><th>不适用</th><th>🔴 卡点合计</th></tr>')
        for b in blockage:
            b_cls = 'badge-red' if b['blocked'] > 100 else ('badge-yellow' if b['blocked'] > 30 else 'badge-green')
            P.append(f'<tr><td><strong>{b["phase"]}</strong></td><td><span class="badge badge-red">{b["pending"]}</span></td><td><span class="badge badge-yellow">{b["in_progress"]}</span></td><td><span class="badge badge-green">{b["done"]}</span></td><td><span class="badge badge-gray">{b["na"]}</span></td><td><span class="badge {b_cls}">{b["blocked"]}</span></td></tr>')
        P.append('</table></div>')

    # 6.2 卡点项目排名
    bp = d.get('phase_blockage_by_project', [])
    if bp:
        top_bp = bp
        P.append(f'<h3>6.2 卡点项目排名（共 {len(top_bp)} 个项目，按总卡点数降序）</h3>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>排名</th><th>项目</th><th>批次</th><th>系统</th><th>总任务</th><th>FS卡点</th><th>业务测试卡点</th><th>TS卡点</th><th>总卡点</th></tr>')
        for i, r in enumerate(top_bp):
            tc = 'badge-red' if r['total_blocked'] > 50 else ('badge-yellow' if r['total_blocked'] > 20 else 'badge-green')
            fs_c = 'badge-red' if r.get('FS卡点', 0) > 10 else ''
            bt_c = 'badge-red' if r.get('业务测试卡点', 0) > 10 else ''
            ts_c = 'badge-red' if r.get('TS卡点', 0) > 10 else ''
            P.append(f'<tr><td>{i+1}</td><td style="text-align:left;font-weight:600">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td style="color:#dc2626;font-weight:600">{r.get("FS卡点", 0)}</td><td style="color:#d97706;font-weight:600">{r.get("业务测试卡点", 0)}</td><td style="color:#7c3aed;font-weight:600">{r.get("TS卡点", 0)}</td><td><span class="badge {tc}">{r["total_blocked"]}</span></td></tr>')
        P.append('</table></div>')

    # 6.3 阶段负责人卡点
    bperson = d.get('phase_blockage_by_person', [])
    if bperson:
        P.append(f'<h3>6.3 阶段负责人卡点（共 {len(bperson)} 人，按总卡点数降序）</h3>')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>排名</th><th>负责人</th><th>FS待处理</th><th>FS进行中</th><th>业务测试待处理</th><th>业务测试进行中</th><th>TS待处理</th><th>TS进行中</th><th>总卡点</th></tr>')
        for i, r in enumerate(bperson):
            tc = 'badge-red' if r['total_blocked'] > 20 else ('badge-yellow' if r['total_blocked'] > 10 else 'badge-green')
            P.append(f'<tr><td>{i+1}</td><td style="text-align:left;font-weight:600">{r["person"]}</td><td>{r["FS_pending"]}</td><td>{r["FS_in_progress"]}</td><td>{r["BT_pending"]}</td><td>{r["BT_in_progress"]}</td><td>{r["TS_pending"]}</td><td>{r["TS_in_progress"]}</td><td><span class="badge {tc}">{r["total_blocked"]}</span></td></tr>')
        P.append('</table></div>')
    P.append('</div></div>')

    # ===== 七、月度趋势 =====
    if d.get('monthly_detail'):
        P.append('<div class="section"><h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>7 月度完成趋势</h2><div class="collapse-body collapsed"><div class="chart-box"><canvas id="monthlyChart"></canvas></div></div></div>')

    # ===== 八、批次上线时间节点 =====
    P.append('<div class="section" style="border-left:4px solid #2563eb">')
    P.append('<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>8 批次上线时间节点 & 开发截止预警</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="alert alert-info">上线时间：A批次 7/31、B批次 8/30、C批次 10/30。开发任务需提前1个月完成。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>上线日期</th><th>开发截止</th><th>距截止</th><th>总任务</th><th>已完成</th><th>已取消</th><th>完成率</th><th>超截止未完成</th><th>已完成但超截止</th><th>状态</th></tr>')
    for r in d['deadline_analysis']:
        rc = 'badge-green' if r['done_rate'] >= 90 else ('badge-yellow' if r['done_rate'] >= 70 else 'badge-red')
        if r['past_due']:
            dl_str = f'<span class="badge badge-red">已超期{-r["days_left"]}天</span>'
            st_str = '<span class="badge badge-red">🔴 已超开发截止</span>'
        elif r['urgent']:
            dl_str = f'<span class="badge badge-yellow">仅剩{r["days_left"]}天</span>'
            st_str = '<span class="badge badge-yellow">🟡 即将截止</span>'
        else:
            dl_str = f'<span class="badge badge-green">还剩{r["days_left"]}天</span>'
            st_str = '<span class="badge badge-green">🟢 正常</span>'
        od_str = f'<span class="badge badge-red">{r["over_dev"]}</span>' if r['over_dev'] > 0 else '-'
        cc_str = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["go_live"]}</td><td style="font-weight:600">{r["dev_deadline"]}</td><td>{dl_str}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc_str}</td><td><span class="badge {rc}">{r["done_rate"]}%</span></td><td>{od_str}</td><td>{r["done_late"]}</td><td>{st_str}</td></tr>')
    P.append('</table></div></div></div>')

    # ===================================================================
    # 板块三：数据质量
    # ===================================================================
    if d.get('quality'):
        q = d['quality']
        total_issues = q.get('total_issues', 0)
        # 必填字段完整度概算
        fca = d.get('field_comp_all', [])
        avg_field_rate = round(sum(f['rate'] for f in fca) / max(len(fca), 1), 1) if fca else 0
        # 验收就绪概算
        total_done_all = sum(a['total_done'] for a in d.get('acc_summary', []))
        total_ready_all = sum(a['all_ready'] for a in d.get('acc_summary', []))
        avg_ready_rate = round(total_ready_all / total_done_all * 100, 1) if total_done_all > 0 else 0

        P.append('<div class="section" style="border-left:4px solid #7c3aed"><h2>📋 数据质量概览</h2>')
        P.append('<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(180px,1fr))">')
        q_cls = 'green' if total_issues == 0 else 'red'
        P.append(f'<div class="kpi-card {q_cls}"><div class="label">🔍 规范违规</div><div class="value">{total_issues}</div></div>')
        f_cls = 'green' if avg_field_rate >= 95 else ('orange' if avg_field_rate >= 80 else 'red')
        P.append(f'<div class="kpi-card {f_cls}"><div class="label">📋 字段完整度</div><div class="value">{avg_field_rate}%</div></div>')
        a_cls = 'green' if avg_ready_rate >= 80 else ('orange' if avg_ready_rate >= 50 else 'red')
        P.append(f'<div class="kpi-card {a_cls}"><div class="label">✅ 验收就绪率</div><div class="value">{avg_ready_rate}%</div></div>')
        P.append('</div>')
        quality_fn = os.path.basename(output_path).replace('_PMO监控分析报告_', '_数据质量专项报告_')
        P.append(f'<div class="alert alert-info" style="margin-top:12px">📊 详细质量分析请查看 <a href="{quality_fn}" style="color:#2563eb;font-weight:600;text-decoration:underline">数据质量专项报告</a> — 包含 6 类规则说明、违规样例、必填字段完整度、验收就绪明细</div>')
        P.append('</div>')

    # ===================================================================
    # 板块五：其他（九 ~ 十）
    # ===================================================================

    # ===== 九、供应商×批次×系统类型 =====
    P.append('<div class="section">')
    P.append('<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>9 供应商团队绩效 — 批次 × 系统类型</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>供应商</th><th>批次</th><th>系统</th><th>总任务</th><th>已完成</th><th>已取消</th><th>未完成</th><th>完成率</th><th>人天</th><th>质量问题</th></tr>')
    for r in d['team_detail']:
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
        # 质量问题交叉引用（团队×批次×系统）
        q_issues = team_quality_map.get((r['team'], r['batch'], r['system']), 0)
        q_str = f'<span class="badge badge-red">{q_issues}</span>' if q_issues > 500 else (f'<span class="badge badge-yellow">{q_issues}</span>' if q_issues > 0 else '<span class="badge badge-green">0</span>')
        cc_str = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
        P.append(f'<tr><td style="text-align:left">{r["team"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc_str}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td><td>{q_str}</td></tr>')
    P.append('</table></div></div></div>')

    # ===== 十、模块×批次×系统类型 =====
    P.append('<div class="section">')
    P.append('<h2 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>10 模块完成率明细 — 批次 × 系统类型</h2>')
    P.append('<div class="collapse-body collapsed">')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>模块</th><th>批次</th><th>系统</th><th>总任务</th><th>已完成</th><th>已取消</th><th>未完成</th><th>完成率</th><th>人天</th><th>质量问题</th></tr>')
    for r in d['module_detail']:
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
        # 质量问题交叉引用（模块×批次×系统）
        q_issues = module_quality_map.get((r['module'], r['batch'], r['system']), 0)
        q_str = f'<span class="badge badge-red">{q_issues}</span>' if q_issues > 500 else (f'<span class="badge badge-yellow">{q_issues}</span>' if q_issues > 0 else '<span class="badge badge-green">0</span>')
        cc_str = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
        P.append(f'<tr><td style="text-align:left">{r["module"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{cc_str}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td><td>{q_str}</td></tr>')
    P.append('</table></div></div></div>')

    P.append(f'<div class="footer"><p>1455项目 PMO监控分析报告 | 自动生成于 {d["generated_at"]} | 数据截止 {d["report_date"]}</p><p>逾期判断：结束日期 < {d["report_date"]} 且未完成 | 临期：{d["report_date"]}后7天内到期</p></div></div>')

    # ===== Charts JS =====
    batch_labels = json.dumps([b['batch'] for b in d['batch_kpi']])
    batch_done = json.dumps([b['done'] for b in d['batch_kpi']])
    batch_undone = json.dumps([b['undone'] for b in d['batch_kpi']])
    sys_labels = json.dumps([s['system'] for s in d['system_kpi']])
    sys_totals = json.dumps([s['total'] for s in d['system_kpi']])
    stage_labels = json.dumps([s['phase'] for s in d.get('phase_blockage', [])])
    stage_pending = json.dumps([s['pending'] for s in d.get('phase_blockage', [])])
    stage_progress = json.dumps([s['in_progress'] for s in d.get('phase_blockage', [])])
    stage_done = json.dumps([s['done'] for s in d.get('phase_blockage', [])])
    stage_na = json.dumps([s['na'] for s in d.get('phase_blockage', [])])

    P.append(f'''<script>
new Chart(document.getElementById('batchBarChart'),{{type:'bar',data:{{labels:{batch_labels},datasets:[{{label:'已完成',data:{batch_done},backgroundColor:'#16a34a'}},{{label:'未完成',data:{batch_undone},backgroundColor:'#ef4444'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{stacked:true}},y:{{stacked:true}}}}}}}});
new Chart(document.getElementById('sysPieChart'),{{type:'doughnut',data:{{labels:{sys_labels},datasets:[{{data:{sys_totals},backgroundColor:['#7c3aed','#2563eb']}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('phaseBlockageChart'),{{type:'bar',data:{{labels:{stage_labels},datasets:[{{label:'待处理',data:{stage_pending},backgroundColor:'#ef4444'}},{{label:'进行中',data:{stage_progress},backgroundColor:'#f97316'}},{{label:'已完成',data:{stage_done},backgroundColor:'#16a34a'}},{{label:'不适用',data:{stage_na},backgroundColor:'#d1d5db'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{stacked:true}},y:{{stacked:true,title:{{display:true,text:'任务数'}}}}}}}}}});
''')

    if d.get('monthly_detail'):
        ml = json.dumps([m['month'] for m in d['monthly_detail']])
        md = json.dumps([m['done'] for m in d['monthly_detail']])
        mt = json.dumps([m['total'] for m in d['monthly_detail']])
        P.append(f'''new Chart(document.getElementById('monthlyChart'),{{type:'line',data:{{labels:{ml},datasets:[{{label:'完成任务',data:{md},borderColor:'#16a34a',backgroundColor:'rgba(22,163,74,.1)',fill:true,tension:.3}},{{label:'总任务',data:{mt},borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.1)',fill:true,tension:.3}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
''')

    modal_js = ("function openModal(id){var m=document.getElementById(id);if(m)"
                "{m.classList.add('active');document.body.style.overflow='hidden'}}"
                "function closeModal(id){var m=document.getElementById(id);if(m)"
                "{m.classList.remove('active');document.body.style.overflow=''}}"
                "document.addEventListener('keydown',function(e){if(e.key==='Escape')"
                "{document.querySelectorAll('.modal-overlay.active').forEach(function(m)"
                "{m.classList.remove('active')});document.body.style.overflow=''}});")
    collapse_js = ("function toggleCollapse(el){el.classList.toggle('collapsed');"
                   "var body=el.nextElementSibling;if(body)body.classList.toggle('collapsed')}")
    P.append(modal_js + collapse_js + '\n</script></body></html>')
    html = '\n'.join(P)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
