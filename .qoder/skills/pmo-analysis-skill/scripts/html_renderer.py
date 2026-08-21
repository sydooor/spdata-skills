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
.kpi-link{color:inherit;text-decoration:none;cursor:pointer;border-bottom:2px dotted currentColor;transition:opacity .2s}
.kpi-link:hover{opacity:.7;border-bottom-style:solid}
.kpi-link-inline{color:#dc2626;text-decoration:none;font-weight:600}
.kpi-link-inline:hover{text-decoration:underline}
*[id]{scroll-margin-top:20px}
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
.modal-content{background:#fff;border-radius:12px;max-width:98vw;width:min(2400px,98vw);max-height:85vh;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.25);display:flex;flex-direction:column}
.modal-header{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #e5e7eb;background:#f8fafc;border-radius:12px 12px 0 0}
.modal-header h3{font-size:16px;color:#1a3a5c;margin:0}
.modal-close{background:none;border:none;font-size:22px;cursor:pointer;color:#6b7280;padding:4px 8px;border-radius:4px;line-height:1}
.modal-close:hover{background:#e5e7eb;color:#1f2937}
.modal-body{overflow-y:auto;padding:16px 20px;flex:1}
.modal-body .table-wrap{max-height:none;overflow-x:auto}
.modal-body table{font-size:11px}
.modal-body table td{white-space:nowrap}
.modal-body table td.modal-wrap{white-space:normal}
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
.section .collapse-body.collapsed{max-height:0}
/* 环比对比 */
.delta-up{color:#16a34a;font-weight:700;font-size:11px;margin-left:2px}
.delta-down{color:#dc2626;font-weight:700;font-size:11px;margin-left:2px}
.delta-flat{color:#9ca3af;font-weight:600;font-size:11px;margin-left:2px}
.new-done-cell{color:#16a34a;font-weight:700}
.new-done-zero{color:#9ca3af}
.proj-trend-link{color:#1d4ed8;font-weight:600;cursor:pointer;text-decoration:underline;text-decoration-style:dotted}
.proj-trend-link:hover{color:#2563eb}
.trend-pair-box{border:1px solid #e5e7eb;border-radius:8px;margin:10px 0;overflow:hidden;font-size:13px}
.trend-pair-box summary{padding:8px 14px;background:#f8fafc;cursor:pointer;font-weight:600;color:#1a3a5c}
.trend-pair-box summary:hover{background:#eff6ff}
.trend-pair-body{padding:8px 14px}
.trend-cat{margin:10px 0 4px;font-weight:600;color:#374151}"""


# ============================================================
# HTML 生成
# ============================================================
def _format_cc(val):
    """Format cancelled count cell: badge if >0, else '0'."""
    return f'<span class="badge badge-gray">{val}</span>' if val > 0 else '0'

def _rate_badge(rate):
    """Return CSS class for a completion rate."""
    return 'badge-green' if rate >= 90 else ('badge-yellow' if rate >= 70 else 'badge-red')


def _delta_badge(delta):
    """Return inline delta span for rate change (百分点). None → '-'"""
    if delta is None:
        return '<span class="delta-flat">-</span>'
    d = round(delta, 1)
    if d > 0:
        return f'<span class="delta-up">↑{d}</span>'
    if d < 0:
        return f'<span class="delta-down">↓{abs(d)}</span>'
    return '<span class="delta-flat">0</span>'


def _new_done_cell(nd):
    """新增完成数单元格（+N 绿色 / 0 灰色）"""
    cls = 'new-done-cell' if nd > 0 else 'new-done-zero'
    sign = '+' if nd > 0 else ''
    return f'<span class="{cls}">{sign}{nd}</span>'


def _delta_inline(pv, cv, mode='up', is_rate=False):
    """数值单元格内联 Δ 角标（当前值后的较上期变化量）。
    mode: 'up' 升为好（绿+红-） / 'down' 降为好（降绿升红） / 'flat' 中性（灰）
    pv/cv 为 None → 无角标 ''"""
    if pv is None or cv is None:
        return ''
    if is_rate:
        d = round(cv - pv, 1)
        if abs(d) < 1e-9:
            return '<span class="delta-flat">0</span>'
        txt = f'{abs(d):.1f}'
    else:
        d = int(round(cv - pv))
        if d == 0:
            return '<span class="delta-flat">0</span>'
        txt = str(abs(d))
    if mode == 'up':
        cls, sign = ('delta-up', '+') if d > 0 else ('delta-down', '-')
    elif mode == 'down':
        cls, sign = ('delta-up', '+') if d < 0 else ('delta-down', '-')
    else:
        cls, sign = 'delta-flat', ('+' if d > 0 else '-')
    return f'<span class="{cls}">{sign}{txt}</span>'

def _append_subtotal_row(P, rows, label, is_grand=False, show_bt=False, prefix=None, trend=None):
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

    # ===== 环比对比（合计行：聚合成员项目的上期/本期数据） =====
    delta_cell = nd_cell = ''
    mh_delta = bt_delta = ''
    d_total = d_done = d_canc = d_rate = d_mh_t = d_mh_c = d_mh_ip = ''
    d_mh_d = d_mh_r = d_l_t = d_l_c = d_l_d = d_l_r = d_l_rate = d_bt_d = d_bt_r = ''
    if trend and trend.get('proj_diff'):
        members = [trend['proj_diff'].get(r['project']) for r in rows]
        members = [m for m in members if m and m.get('has_prev')]
        if members:
            def _r(v_done, v_total, v_canc):
                return round(v_done / (v_total - v_canc) * 100, 1) if (v_total - v_canc) > 0 else 0
            p_r = _r(sum(m['prev']['done'] for m in members), sum(m['prev']['total'] for m in members), sum(m['prev']['cancelled'] for m in members))
            c_r = _r(sum(m['curr']['done'] for m in members), sum(m['curr']['total'] for m in members), sum(m['curr']['cancelled'] for m in members))
            delta_cell = f'<td>{_delta_badge(round(c_r - p_r, 1))}</td>'
            nd_cell = f'<td>{_new_done_cell(sum(m["new_done"] for m in members))}</td>'
            p_mh = _r(sum(m['prev']['mh_done'] for m in members), sum(m['prev']['mh_total'] for m in members), sum(m['prev']['mh_cancelled'] for m in members))
            c_mh = _r(sum(m['curr']['mh_done'] for m in members), sum(m['curr']['mh_total'] for m in members), sum(m['curr']['mh_cancelled'] for m in members))
            mh_delta = _delta_badge(round(c_mh - p_mh, 1))
            if show_bt:
                p_bt = _r(sum(m['prev']['bt_done'] for m in members), sum(m['prev']['bt_total'] for m in members), 0)
                c_bt = _r(sum(m['curr']['bt_done'] for m in members), sum(m['curr']['bt_total'] for m in members), 0)
                bt_delta = _delta_badge(round(c_bt - p_bt, 1))
            # ===== 全列内联 Δ（聚合成员项目上期/本期） =====
            def _s(field, cvt=lambda x: x):
                pv, cv = cvt(sum(m['prev'][field] for m in members)), cvt(sum(m['curr'][field] for m in members))
                return pv, cv
            pv_t, cv_t = _s('total')
            pv_d, cv_d = _s('done')
            pv_c, cv_c = _s('cancelled')
            d_total = _delta_inline(pv_t, cv_t, 'flat')
            d_done = _delta_inline(pv_d, cv_d, 'up')
            d_canc = _delta_inline(pv_c, cv_c, 'flat')
            d_rate = _delta_inline(p_r, c_r, 'up', is_rate=True)
            pv_mt, cv_mt = _s('mh_total')
            pv_mc, cv_mc = _s('mh_cancelled')
            pv_mip, cv_mip = _s('mh_in_progress')
            pv_md, cv_md = _s('mh_done')
            pv_mr, cv_mr = _s('mh_remaining')
            d_mh_t = _delta_inline(pv_mt, cv_mt, 'flat')
            d_mh_c = _delta_inline(pv_mc, cv_mc, 'flat')
            d_mh_ip = _delta_inline(pv_mip, cv_mip, 'flat')
            d_mh_d = _delta_inline(pv_md, cv_md, 'up')
            d_mh_r = _delta_inline(pv_mr, cv_mr, 'down')
            pv_lt, cv_lt = _s('l_total')
            pv_lc, cv_lc = _s('l_cancelled')
            pv_ld, cv_ld = _s('l_done')
            pv_lr, cv_lr = _s('l_remaining')
            d_l_t = _delta_inline(pv_lt, cv_lt, 'flat')
            d_l_c = _delta_inline(pv_lc, cv_lc, 'flat')
            d_l_d = _delta_inline(pv_ld, cv_ld, 'up')
            d_l_r = _delta_inline(pv_lr, cv_lr, 'down')
            d_l_rate = _delta_inline(_r(pv_ld, pv_lt, pv_lc), _r(cv_ld, cv_lt, cv_lc), 'up', is_rate=True)
            if show_bt:
                pv_bd, cv_bd = _s('bt_done')
                pv_br, cv_br = _s('bt_remaining')
                d_bt_d = _delta_inline(pv_bd, cv_bd, 'up')
                d_bt_r = _delta_inline(pv_br, cv_br, 'down')
        else:
            delta_cell = '<td><span class="delta-flat">-</span></td>'
            nd_cell = '<td><span class="new-done-zero">-</span></td>'

    bt_cols = ''
    if show_bt:
        bt_d = sum(r.get('bt_done', 0) for r in rows)
        bt_r = sum(r.get('bt_remaining', 0) for r in rows)
        bt_t = sum(r.get('bt_total', 0) for r in rows)
        bt_rate_val = round(bt_d / bt_t * 100, 1) if bt_t > 0 else 0
        bt_rc = _rate_badge(bt_rate_val)
        bt_cols = f'<td><strong>{bt_d}</strong>{d_bt_d}</td><td><span style="color:#dc2626;font-weight:700">{bt_r}</span>{d_bt_r}</td><td><span class="badge {bt_rc}"><strong>{bt_rate_val}%</strong></span>{bt_delta}</td>'
    # 合计行中高/低剩余可点击（合并全量明细弹窗，与 _render_modals 的 total 弹窗对应）
    mh_all = [t for r in rows for t in r.get('mh_remaining_tasks', [])] if prefix else []
    low_all = [t for r in rows for t in r.get('l_remaining_tasks', [])] if prefix else []
    if is_grand and mh_all:
        mh_m_cell = f'<td><span class="mh-remaining-link" onclick="openModal(\'{prefix}_mh_modal_total\')">{mh_m}</span>{d_mh_r}</td>'
    else:
        mh_m_cell = f'<td><span style="color:#dc2626;font-weight:700">{mh_m}</span>{d_mh_r}</td>'
    if is_grand and low_all:
        l_m_cell = f'<td><span class="mh-remaining-link" onclick="openModal(\'{prefix}_low_modal_total\')">{l_m}</span>{d_l_r}</td>'
    else:
        l_m_cell = f'<td><span style="color:#dc2626;font-weight:700">{l_m}</span>{d_l_r}</td>'
    P.append(f'<tr style="font-weight:{"700" if is_grand else "600"};background:{bg};{border_style}"><td><strong>{label}</strong></td><td>-</td><td><strong>{t_all}</strong>{d_total}</td><td><strong>{d_all}</strong>{d_done}</td><td>{_format_cc(c_all)}{d_canc}</td><td><span class="badge {rc}"><strong>{rate}%</strong></span>{d_rate}</td>{delta_cell}{nd_cell}<td><strong>{mh_t}</strong>{d_mh_t}</td><td>{_format_cc(mh_c)}{d_mh_c}</td><td><strong>{mh_ip}</strong>{d_mh_ip}</td><td><strong>{mh_d}</strong>{d_mh_d}</td>{mh_m_cell}<td><span class="badge {mh_rc}"><strong>{mh_rate}%</strong></span>{mh_delta}</td><td><strong>{l_t}</strong>{d_l_t}</td><td>{_format_cc(l_c)}{d_l_c}</td><td><strong>{l_d}</strong>{d_l_d}</td>{l_m_cell}<td><span class="badge {l_rc}"><strong>{l_rate}%</strong></span>{d_l_rate}</td>{bt_cols}</tr>')


def _render_row(P, r, modal_idx, prefix, show_bt=False, trend=None):
    """Render a single data row for a batch project matrix."""
    rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
    mh_rc = 'badge-green' if r['mh_rate'] >= 90 else ('badge-yellow' if r['mh_rate'] >= 70 else 'badge-red')
    l_rc = 'badge-green' if r['l_rate'] >= 90 else ('badge-yellow' if r['l_rate'] >= 70 else 'badge-red')
    sc = 'badge-purple' if r['system'] == 'JAVA-专业系统' else 'badge-blue'
    cc = f'<span class="badge badge-gray">{r.get("cancelled", 0)}</span>' if r.get('cancelled', 0) > 0 else '0'
    mh_cc_str = f'<span class="badge badge-gray">{r["mh_cancelled"]}</span>' if r.get('mh_cancelled', 0) > 0 else '0'
    l_cc_str = f'<span class="badge badge-gray">{r["l_cancelled"]}</span>' if r.get('l_cancelled', 0) > 0 else '0'

    # ===== 环比对比列（较上期Δ / 新增完成）+ 项目名多日变化入口 =====
    pd = trend['proj_diff'].get(r['project']) if (trend and trend.get('proj_diff')) else None
    d_total = d_done = d_canc = d_rate = d_mh_t = d_mh_c = d_mh_ip = ''
    d_mh_d = d_mh_r = d_l_t = d_l_c = d_l_d = d_l_r = d_l_rate = d_bt_d = d_bt_r = ''
    if pd and pd.get('has_prev'):
        pv, cv = pd['prev'], pd['curr']
        delta_cell = f'<td>{_delta_badge(round(pd["curr"]["rate"] - pd["prev"]["rate"], 1))}</td>'
        nd_cell = f'<td>{_new_done_cell(pd["new_done"])}</td>'
        mh_delta = _delta_badge(round(pd['curr']['mh_rate'] - pd['prev']['mh_rate'], 1))
        bt_delta = _delta_badge(round(pd['curr']['bt_rate'] - pd['prev']['bt_rate'], 1)) if show_bt else ''
        # ===== 全列内联 Δ（总任务/已完成/已取消/完成率/中高/低/测试） =====
        d_total = _delta_inline(pv['total'], cv['total'], 'flat')
        d_done = _delta_inline(pv['done'], cv['done'], 'up')
        d_canc = _delta_inline(pv['cancelled'], cv['cancelled'], 'flat')
        d_rate = _delta_inline(pv['rate'], cv['rate'], 'up', is_rate=True)
        d_mh_t = _delta_inline(pv['mh_total'], cv['mh_total'], 'flat')
        d_mh_c = _delta_inline(pv['mh_cancelled'], cv['mh_cancelled'], 'flat')
        d_mh_ip = _delta_inline(pv['mh_in_progress'], cv['mh_in_progress'], 'flat')
        d_mh_d = _delta_inline(pv['mh_done'], cv['mh_done'], 'up')
        d_mh_r = _delta_inline(pv['mh_remaining'], cv['mh_remaining'], 'down')
        d_l_t = _delta_inline(pv['l_total'], cv['l_total'], 'flat')
        d_l_c = _delta_inline(pv['l_cancelled'], cv['l_cancelled'], 'flat')
        d_l_d = _delta_inline(pv['l_done'], cv['l_done'], 'up')
        d_l_r = _delta_inline(pv['l_remaining'], cv['l_remaining'], 'down')
        d_l_rate = _delta_inline(pv['l_rate'], cv['l_rate'], 'up', is_rate=True)
        if show_bt:
            d_bt_d = _delta_inline(pv['bt_done'], cv['bt_done'], 'up')
            d_bt_r = _delta_inline(pv['bt_remaining'], cv['bt_remaining'], 'down')
    elif trend and trend.get('proj_diff'):
        delta_cell = '<td><span class="delta-flat">新增</span></td>'
        nd_cell = '<td><span class="new-done-zero">-</span></td>'
        mh_delta = bt_delta = ''
    else:
        delta_cell = nd_cell = mh_delta = bt_delta = ''
    if trend and trend.get('series', {}).get(r['project']):
        proj_cell = f'<td style="text-align:left;font-weight:500"><span class="proj-trend-link" onclick="openModal(\'{prefix}_trend_{modal_idx}\')">{r["project"]}</span></td>'
    else:
        proj_cell = f'<td style="text-align:left;font-weight:500">{r["project"]}</td>'

    if r.get('mh_remaining_tasks') and len(r['mh_remaining_tasks']) > 0:
        modal_id = f'{prefix}_mh_modal_{modal_idx}'
        mh_cell = f'<td><span class="mh-remaining-link" onclick="openModal(\'{modal_id}\')">{r["mh_remaining"]}</span>{d_mh_r}</td>'
    else:
        modal_id = None
        mh_cell = f'<td><span style="color:#6b7280">{r["mh_remaining"]}</span>{d_mh_r}</td>'
    # 中高进行中 — clickable if tasks exist
    mh_ip = r.get('mh_in_progress', 0)
    if r.get('mh_in_progress_tasks') and len(r['mh_in_progress_tasks']) > 0:
        mh_ip_modal_id = f'{prefix}_mhip_modal_{modal_idx}'
        mh_ip_cell = f'<td><span class="mh-inprogress-link" onclick="openModal(\'{mh_ip_modal_id}\')">{mh_ip}</span>{d_mh_ip}</td>'
    else:
        mh_ip_modal_id = None
        mh_ip_cell = f'<td><span style="color:#6b7280">{mh_ip}</span>{d_mh_ip}</td>'
    if show_bt:
        bt_rate_val = r.get('bt_rate', 0)
        bt_rc = 'badge-green' if bt_rate_val >= 90 else ('badge-yellow' if bt_rate_val >= 70 else 'badge-red')
        if r.get('bt_remaining_tasks') and len(r['bt_remaining_tasks']) > 0:
            bt_modal_id = f'{prefix}_bt_modal_{modal_idx}'
            bt_cell = f'<td><span class="bt-remaining-link" onclick="openModal(\'{bt_modal_id}\')">{r["bt_remaining"]}</span>{d_bt_r}</td>'
        else:
            bt_modal_id = None
            bt_cell = f'<td><span style="color:#6b7280">{r["bt_remaining"]}</span>{d_bt_r}</td>'
        bt_cols = f'<td>{r["bt_done"]}{d_bt_d}</td>{bt_cell}<td><span class="badge {bt_rc}">{bt_rate_val}%</span>{bt_delta}</td>'
    else:
        bt_cols = ''
        bt_modal_id = None
    # 低剩余 — clickable if tasks exist
    if r.get('l_remaining_tasks') and len(r['l_remaining_tasks']) > 0:
        low_modal_id = f'{prefix}_low_modal_{modal_idx}'
        l_cell = f'<td><span class="mh-remaining-link" onclick="openModal(\'{low_modal_id}\')">{r["l_remaining"]}</span>{d_l_r}</td>'
    else:
        low_modal_id = None
        l_cell = f'<td><span style="color:#dc2626;font-weight:600">{r["l_remaining"]}</span>{d_l_r}</td>'
    P.append(f'<tr><td><span class="badge {sc}">{r["system"]}</span></td>{proj_cell}<td>{r["total"]}{d_total}</td><td>{r["done"]}{d_done}</td><td>{cc}{d_canc}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span>{d_rate}</td>{delta_cell}{nd_cell}<td>{r["mh_total"]}{d_mh_t}</td><td>{mh_cc_str}{d_mh_c}</td>{mh_ip_cell}<td>{r["mh_done"]}{d_mh_d}</td>{mh_cell}<td><span class="badge {mh_rc}">{r["mh_rate"]}%</span>{mh_delta}</td><td>{r["l_total"]}{d_l_t}</td><td>{l_cc_str}{d_l_c}</td><td>{r["l_done"]}{d_l_d}</td>{l_cell}<td><span class="badge {l_rc}">{r["l_rate"]}%</span>{d_l_rate}</td>{bt_cols}</tr>')

def _task_modal(P, modal_id, title, tasks):
    """通用任务明细弹窗（27列：核心字段 + 全部计划时间 + 阶段状态）"""
    P.append(f'<div class="modal-overlay" id="{modal_id}" onclick="if(event.target===this)closeModal(\'{modal_id}\')">')
    P.append(f'<div class="modal-content">')
    P.append(f'<div class="modal-header"><h3>{title}（{len(tasks)}条）</h3><button class="modal-close" onclick="closeModal(\'{modal_id}\')">&times;</button></div>')
    P.append(f'<div class="modal-body"><div class="table-wrap"><table>')
    P.append('<tr><th>#</th><th>项目</th><th>任务</th><th>任务类型</th><th>选择类型</th><th>模块</th><th>优先级</th><th>状态</th><th>负责人</th><th>进度</th><th>开始日期</th><th>结束日期</th><th>人天</th><th>FS状态</th><th>FS负责人</th><th>FS计划结束</th><th>FS实际结束</th><th>业务测试状态</th><th>业务测试负责人</th><th>业务测试计划开始</th><th>业务测试计划结束</th><th>业务测试实际开始</th><th>业务测试实际结束</th><th>TS状态</th><th>TS计划结束</th><th>TS实际结束</th><th>延期原因</th><th>备注</th></tr>')
    for ti, t in enumerate(tasks, 1):
        pc = 'badge-red' if t['priority'] == '高' else ('badge-yellow' if t['priority'] == '中' else 'badge-gray')
        fs_cls = 'badge-green' if t['fs_status'] == '已完成' else ('badge-yellow' if t['fs_status'] == '进行中' else ('badge-red' if t['fs_status'] == '待处理' else 'badge-gray'))
        bt_cls = 'badge-green' if t['bt_status'] == '已完成' else ('badge-yellow' if t['bt_status'] == '进行中' else ('badge-red' if t['bt_status'] == '待处理' else 'badge-gray'))
        ts_cls = 'badge-green' if t['ts_status'] == '已完成' else ('badge-yellow' if t['ts_status'] == '进行中' else ('badge-red' if t['ts_status'] == '待处理' else 'badge-gray'))
        reason = t.get('reason', '') if t.get('reason', '') else '-'
        P.append(f'<tr><td>{ti}</td><td style="text-align:left">{t["project"]}</td><td style="text-align:left">{t["task"]}</td><td>{t["task_type"]}</td><td>{t["select_type"]}</td><td>{t["module"]}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["status"]}</td><td>{t["person"]}</td><td>{t["progress"]}</td><td>{t["start"]}</td><td>{t["end"]}</td><td>{t["days"]}</td><td><span class="badge {fs_cls}">{t["fs_status"]}</span></td><td>{t["fs_person"]}</td><td>{t["fs_plan_end"]}</td><td>{t["fs_actual_end"]}</td><td><span class="badge {bt_cls}">{t["bt_status"]}</span></td><td>{t["bt_person"]}</td><td>{t["bt_plan_start"]}</td><td>{t["bt_plan_end"]}</td><td>{t["bt_actual_start"]}</td><td>{t["bt_actual_end"]}</td><td><span class="badge {ts_cls}">{t["ts_status"]}</span></td><td>{t["ts_plan_end"]}</td><td>{t["ts_actual_end"]}</td><td class="modal-wrap" style="text-align:left;font-size:11px;max-width:220px">{reason}</td><td class="modal-wrap" style="text-align:left;font-size:11px;max-width:220px">{t["remark"]}</td></tr>')
    P.append('</table></div></div></div></div>')


def _bt_task_modal(P, modal_id, title, tasks):
    """业务测试剩余任务弹窗：复用全字段明细（同 _task_modal 列结构）"""
    _task_modal(P, modal_id, title, tasks)


def _render_modals(P, bp, prefix, show_bt=False):
    """Render modal popups for a batch project matrix (MH/LOW remaining, MH in-progress, grand-total, BT)."""
    mi = 0
    for r in bp:
        if r.get('mh_remaining_tasks'):
            _task_modal(P, f'{prefix}_mh_modal_{mi}', f'📋 {r["system"]} · {r["project"]} — 中高优先级剩余任务', r['mh_remaining_tasks'])
        if r.get('mh_in_progress_tasks'):
            _task_modal(P, f'{prefix}_mhip_modal_{mi}', f'🔄 {r["system"]} · {r["project"]} — 中高优先级进行中任务', r['mh_in_progress_tasks'])
        if r.get('l_remaining_tasks'):
            _task_modal(P, f'{prefix}_low_modal_{mi}', f'📋 {r["system"]} · {r["project"]} — 低优先级剩余任务', r['l_remaining_tasks'])
        mi += 1

    # Grand total modals（合计行点击：合并全量明细）
    mh_all = [t for r in bp for t in r.get('mh_remaining_tasks', [])]
    low_all = [t for r in bp for t in r.get('l_remaining_tasks', [])]
    if mh_all:
        _task_modal(P, f'{prefix}_mh_modal_total', f'📋 合计 — 中高优先级剩余任务（全量）', mh_all)
    if low_all:
        _task_modal(P, f'{prefix}_low_modal_total', f'📋 合计 — 低优先级剩余任务（全量）', low_all)

    # BT modals（业务测试剩余）
    if show_bt:
        bt_mi = 0
        for r in bp:
            if r.get('bt_remaining_tasks'):
                _bt_task_modal(P, f'{prefix}_bt_modal_{bt_mi}', f'🧪 {r["system"]} · {r["project"]} — 业务测试剩余任务', r['bt_remaining_tasks'])
            bt_mi += 1

def _render_trend_modals(P, bp, prefix, trend):
    """Render per-project multi-day comparison modals（点开项目名查看多日变化明细）"""
    if not trend or not trend.get('series') or not trend.get('pairs'):
        return
    for mi, r in enumerate(bp):
        proj = r['project']
        series = trend['series'].get(proj)
        if not series:
            continue
        modal_id = f'{prefix}_trend_{mi}'
        P.append(f'<div class="modal-overlay" id="{modal_id}" onclick="if(event.target===this)closeModal(\'{modal_id}\')">')
        P.append('<div class="modal-content">')
        P.append(f'<div class="modal-header"><h3>📈 {proj} — 多日变化对比（{len(series)} 个快照）</h3><button class="modal-close" onclick="closeModal(\'{modal_id}\')">&times;</button></div>')
        P.append('<div class="modal-body">')

        # ===== 多日对比表：数量变化 + 进度变化（全指标覆盖） =====
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>快照日期</th><th>总任务</th><th>已完成</th><th>进行中</th><th>待处理</th><th>已取消</th><th>完成率</th><th>较前一日</th><th>当日新增完成</th><th>中高已完成</th><th>中高剩余</th><th>中高完成率</th><th>低已完成</th><th>低剩余</th><th>低完成率</th><th>测试已完成</th><th>测试剩余</th><th>测试完成率</th></tr>')
        for i, s in enumerate(series):
            if s is None:
                P.append(f'<tr><td>{trend["dates"][i]}</td><td colspan="17" style="color:#9ca3af">（该快照中无此项目）</td></tr>')
                continue
            if i > 0 and series[i - 1] is not None:
                dcell = _delta_badge(round(s['rate'] - series[i - 1]['rate'], 1))
            else:
                dcell = '<span class="delta-flat">-</span>'
            nd = '-'
            if i > 0 and i - 1 < len(trend['pairs']):
                pdiff = trend['pairs'][i - 1]['diff'].get(proj)
                if pdiff and pdiff.get('has_prev'):
                    nd = _new_done_cell(pdiff['new_done'])
            P.append(f'<tr><td>{s["date"]}</td><td>{s["total"]}</td><td style="color:#16a34a;font-weight:600">{s["done"]}</td><td style="color:#2563eb">{s["in_progress"]}</td><td style="color:#d97706">{s["pending"]}</td><td>{s["cancelled"]}</td><td><span class="badge {_rate_badge(s["rate"])}">{s["rate"]}%</span></td><td>{dcell}</td><td>{nd}</td><td>{s["mh_done"]}</td><td style="color:#dc2626">{s["mh_remaining"]}</td><td><span class="badge {_rate_badge(s["mh_rate"])}">{s["mh_rate"]}%</span></td><td>{s["l_done"]}</td><td style="color:#dc2626">{s["l_remaining"]}</td><td><span class="badge {_rate_badge(s["l_rate"])}">{s["l_rate"]}%</span></td><td>{s["bt_done"]}</td><td style="color:#dc2626">{s["bt_remaining"]}</td><td><span class="badge {_rate_badge(s["bt_rate"])}">{s["bt_rate"]}%</span></td></tr>')
        P.append('</table></div>')

        # ===== 各期任务级变化明细（默认展开最近一期） =====
        def _chg_table(title, items, headers, row_fn):
            P.append(f'<div class="trend-cat">{title}（{len(items)}条）</div>')
            if not items:
                P.append('<div style="color:#9ca3af;font-size:12px">无</div>')
                return
            P.append('<div class="table-wrap"><table>')
            P.append('<tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr>')
            for it in items:
                P.append('<tr>' + ''.join(f'<td>{c}</td>' for c in row_fn(it)) + '</tr>')
            P.append('</table></div>')

        for pi, pair in enumerate(trend['pairs']):
            diff = pair['diff'].get(proj)
            if diff is None:
                continue
            if not diff.get('has_prev'):
                P.append(f'<div class="alert alert-warn" style="font-size:12px">⚠️ {pair["curr_date"]}：本项目为该期新增（无 {pair["prev_date"]} 数据）。</div>')
                continue
            summary = f'{pair["prev_date"]} → {pair["curr_date"]} 变化明细：新完成 {diff["new_done"]} | 进度提升 {diff["progress_up"]} | 新启动 {diff["started"]} | 状态回退 {diff["regressed"]} | 测试完成 {diff["bt_new_done"]} | 新提测 {diff["bt_started"]} | 测试回退 {diff["bt_regressed"]} | 新增 {diff["added"]} / 消失 {diff["removed"]}'
            open_attr = ' open' if pi == len(trend['pairs']) - 1 else ''
            P.append(f'<details class="trend-pair-box"{open_attr}><summary>{summary}</summary><div class="trend-pair-body">')
            _chg_table('📗 新完成任务', diff['new_done_list'], ['任务', '负责人', '变化'], lambda t: [t['task'], t['person'], f'{t["before"]} → {t["after"]}'])
            _chg_table('📈 进度提升任务', diff['progress_up_list'], ['任务', '负责人', '进度变化'], lambda t: [t['task'], t['person'], f'{t["before"].split()[1]} → {t["after"].split()[1]}'])
            _chg_table('▶ 新启动任务', diff['started_list'], ['任务', '负责人', '变化'], lambda t: [t['task'], t['person'], f'{t["before"]} → {t["after"]}'])
            _chg_table('↺ 状态回退任务', diff['regressed_list'], ['任务', '负责人', '变化'], lambda t: [t['task'], t['person'], f'{t["before"]} → {t["after"]}'])
            _chg_table('🧪 测试完成任务', diff['bt_done_new_list'], ['任务', '测试负责人', '变化'], lambda t: [t['task'], t['person'], f'{t["bt_before"]} → {t["bt_after"]}'])
            _chg_table('🧪 新提测任务', diff['bt_started_list'], ['任务', '测试负责人', '变化'], lambda t: [t['task'], t['person'], f'{t["bt_before"]} → {t["bt_after"]}'])
            _chg_table('🧪 测试回退任务', diff['bt_regressed_list'], ['任务', '测试负责人', '变化'], lambda t: [t['task'], t['person'], f'{t["bt_before"]} → {t["bt_after"]}'])
            add_rm = [dict(t, tag='➕新增') for t in diff['added_list']] + [dict(t, tag='➖消失') for t in diff['removed_list']]
            _chg_table('➕➖ 新增 / 消失任务', add_rm, ['类型', '任务', '负责人'], lambda t: [t['tag'], t['task'], t['person']])
            P.append('</div></details>')

        P.append('</div></div></div>')


def _render_batch_matrix(P, bp, batch_label, batch_letter, show_bt=False, subsection_num=None, trend=None):
    """Render a full batch project matrix with inline SAP/JAVA subtotals and modals."""
    if not bp:
        return
    has_trend = bool(trend and trend.get('proj_diff'))
    if subsection_num:
        P.append(f'<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>{subsection_num} {batch_label} · 系统类型 × 项目 — 完成进度</h3>')
        P.append(f'<div class="collapse-body collapsed">')
    else:
        P.append(f'<div class="section"><h2>一、{batch_label} · 系统类型 × 项目 — 完成进度</h2>')
    trend_note = ''
    if has_trend:
        trend_note = f'<br><small style="color:#555">📈 各列数值后的 <span class="delta-up">+n</span>/<span class="delta-down">-n</span> 为较上期变化（绿=推进，红=倒退，灰=持平；测试剩余类减少为绿）；点击<strong>项目名</strong>查看多日变化明细。对比基准快照：<strong>{trend["base_date"]}</strong>（间隔 {trend["base_interval"]} 天）</small>'
    P.append(f'<div class="alert alert-info">{batch_label}按<span style="font-weight:600;color:#1d4ed8">系统类型</span>×<span style="font-weight:600;color:#059669">项目</span>下钻视图，按完成率升序排列。{trend_note}</div>')
    P.append('<div class="table-wrap"><table>')
    bt_header = '<th>测试已完成</th><th>测试剩余</th><th>测试完成率</th>' if show_bt else ''
    trend_header = '<th>较上期Δ</th><th>新增完成</th>' if has_trend else ''
    P.append(f'<tr><th>系统类型</th><th>项目</th><th>总任务</th><th>已完成</th><th>已取消</th><th>整体完成率</th>{trend_header}<th>中高总数</th><th>中高已取消</th><th>中高进行中</th><th>中高已完成</th><th>中高剩余</th><th>中高完成率</th><th>低总数</th><th>低已取消</th><th>低已完成</th><th>低剩余</th><th>低完成率</th>{bt_header}</tr>')

    sap_rows = [r for r in bp if r['system'] == 'SAP']
    java_rows = [r for r in bp if r['system'] == 'JAVA-专业系统']
    prefix = batch_letter.lower()

    # Render SAP rows then SAP subtotal inline
    modal_idx = 0
    for r in sap_rows:
        _render_row(P, r, modal_idx, prefix, show_bt, trend=trend)
        modal_idx += 1
    _append_subtotal_row(P, sap_rows, '📊 SAP 小计', show_bt=show_bt, prefix=prefix, trend=trend)

    # Render JAVA rows then JAVA subtotal inline
    for r in java_rows:
        _render_row(P, r, modal_idx, prefix, show_bt, trend=trend)
        modal_idx += 1
    _append_subtotal_row(P, java_rows, '📊 JAVA 小计', show_bt=show_bt, prefix=prefix, trend=trend)

    # Grand total
    _append_subtotal_row(P, bp, '📊 合计', is_grand=True, show_bt=show_bt, prefix=prefix, trend=trend)
    P.append('</table></div>')

    # Modals (MH remaining / MH in-progress / LOW remaining / grand total / BT)
    _render_modals(P, bp, prefix, show_bt)
    # 项目多日变化弹窗
    _render_trend_modals(P, bp, prefix, trend)
    if subsection_num:
        P.append('</div></div>')  # close collapse-body and subsection
    else:
        P.append('</div>')


def generate_html(d, output_path):
    P = []  # parts
    trend = d.get('trend')  # 历史快照多日对比数据（无历史快照时为 None）

    # ===== 构建质量维度查找映射（供各章节交叉引用） =====
    proj_quality_map = {}
    bs_quality_map = {}

    if d.get('quality'):
        q = d['quality']
        is_rich = 'summary' in q
        if is_rich and q.get('by_project'):
            for pq in q['by_project']:
                proj_quality_map[pq['project']] = pq['total']
        if is_rich and q.get('by_batch_system'):
            for bsq in q['by_batch_system']:
                bs_quality_map[(bsq['batch'], bsq['system'])] = bsq['total']


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
    # 中高剩余弹窗（复用全字段 32 列明细）
    for idx, r in enumerate(sbp):
        tasks = r.get('mh_remaining_tasks', [])
        if not tasks:
            continue
        _task_modal(P, f'mh_modal_{idx}', f'📋 {r["system"]} · {r["batch"]} — 中高优先级剩余任务', tasks)
    # ===== 1.1 / 1.2 / 1.3 批次 · 系统类型 × 项目 — 完成进度 =====
    _render_batch_matrix(P, d.get('a_batch_project_priority', []), 'A批次', 'A', subsection_num='1.1', trend=trend)
    _render_batch_matrix(P, d.get('b_batch_project_priority', []), 'B批次', 'B', subsection_num='1.2', trend=trend)
    _render_batch_matrix(P, d.get('c_batch_project_priority', []), 'C批次', 'C', show_bt=True, subsection_num='1.3', trend=trend)
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



    # ===== Charts JS =====
    batch_labels = json.dumps([b['batch'] for b in d['batch_kpi']])
    batch_done = json.dumps([b['done'] for b in d['batch_kpi']])
    batch_undone = json.dumps([b['undone'] for b in d['batch_kpi']])
    sys_labels = json.dumps([s['system'] for s in d['system_kpi']])
    sys_totals = json.dumps([s['total'] for s in d['system_kpi']])

    P.append(f'''<script>
new Chart(document.getElementById('batchBarChart'),{{type:'bar',data:{{labels:{batch_labels},datasets:[{{label:'已完成',data:{batch_done},backgroundColor:'#16a34a'}},{{label:'未完成',data:{batch_undone},backgroundColor:'#ef4444'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{stacked:true}},y:{{stacked:true}}}}}}}});
new Chart(document.getElementById('sysPieChart'),{{type:'doughnut',data:{{labels:{sys_labels},datasets:[{{data:{sys_totals},backgroundColor:['#7c3aed','#2563eb']}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
''')



    P.append('</script>')

    modal_js = ("function openModal(id){var m=document.getElementById(id);if(m)"
                "{m.classList.add('active');document.body.style.overflow='hidden'}}"
                "function closeModal(id){var m=document.getElementById(id);if(m)"
                "{m.classList.remove('active');document.body.style.overflow=''}}"
                "document.addEventListener('keydown',function(e){if(e.key==='Escape')"
                "{document.querySelectorAll('.modal-overlay.active').forEach(function(m)"
                "{m.classList.remove('active')});document.body.style.overflow=''}});")
    collapse_js = ("function toggleCollapse(el){el.classList.toggle('collapsed');"
                   "var body=el.nextElementSibling;if(body)body.classList.toggle('collapsed')}"
                   "function expandTarget(hash){if(!hash)return;var el=document.querySelector(hash);"
                   "if(!el)return;var body=el.closest('.collapse-body');"
                   "if(body&&body.classList.contains('collapsed')){var toggle=body.previousElementSibling;"
                   "if(toggle&&toggle.classList.contains('collapse-toggle'))toggleCollapse(toggle)}"
                   "setTimeout(function(){el.scrollIntoView({behavior:'smooth',block:'start'})},100)}"
                   "window.addEventListener('hashchange',function(){expandTarget(location.hash)});"
                   "window.addEventListener('load',function(){setTimeout(function(){expandTarget(location.hash)},200)})")
    # ===================================================================
    # BPC前端-独立开发批次 专项监控（放在报告最后）
    # ===================================================================
    bpc = d.get('bpc_stats')
    if bpc:
        if bpc['deadline_status'] == 'past_due':
            dl_icon, dl_cls = '🔴', 'red'
        elif bpc['deadline_status'] == 'urgent':
            dl_icon, dl_cls = '🟡', 'orange'
        else:
            dl_icon, dl_cls = '🟢', 'green'

        def _bpc_badge(status):
            return 'badge-green' if status == '已完成' else ('badge-yellow' if status == '进行中' else ('badge-red' if status == '待处理' else 'badge-gray'))

        P.append('<div class="section" style="border-left:4px solid #f59e0b">')
        P.append('<h2>🔶 BPC前端-独立开发批次 专项监控</h2>')
        ua_hint = f'，<a href="#bpc-unassigned" class="kpi-link-inline">未分配负责人：<strong style="color:#dc2626">{bpc.get("unassigned_count", 0)}</strong> 条</a>' if bpc.get('unassigned_count', 0) > 0 else ''
        P.append(f'<div class="alert alert-info">BPC前端属于 <strong>JAVA-专业系统</strong>，不跟随A/B/C批次。主计划开发完成：<strong style="font-size:16px">{bpc["deadline"]}</strong>（{bpc["deadline_label"]}）。{bpc["total"]} 条任务，{bpc["people"]} 名负责人（含未分配）。{ua_hint}<br><small style="color:#888">💡 点击 KPI 卡片中的数字可跳转到对应详情；表格中蓝色数字可点击查看全量明细弹窗</small></div>')

        P.append('<div class="kpi-grid">')
        kpi_items = [
            ('BPC 总任务', str(bpc['total']), 'blue', None),
            ('已完成', f"{bpc['done']} / {bpc['comp_rate']}%", 'green' if bpc['comp_rate'] >= 70 else 'orange', 'bpc-acceptance'),
            ('未完成', str(bpc['undone']), 'orange', 'bpc-risk'),
            ('⚠️ 逾期 / 临期', f"{bpc['overdue']} / {bpc['near_due']}", 'red' if bpc['overdue'] > 0 else ('purple' if bpc['near_due'] > 0 else 'green'), 'bpc-risk'),
            ('⚠️ 计划缺失', str(bpc['plan_missing_count']), 'red' if bpc['plan_missing_count'] > 0 else 'green', 'bpc-plan-missing'),
            ('🧪 业务测试剩余', str(bpc['bt_remaining']), 'purple' if bpc['bt_remaining'] > 0 else 'green', 'bpc-overview'),
            ('总人天', str(bpc['total_days']), 'blue', 'bpc-man-day'),
            (f'{dl_icon} 距截止', bpc['deadline_label'], dl_cls, None),
        ]
        for label, val, cls, anchor in kpi_items:
            v_html = f'<a href="#{anchor}" class="kpi-link">{val}</a>' if anchor else val
            P.append(f'<div class="kpi-card {cls}"><div class="label">{label}</div><div class="value">{v_html}</div></div>')
        P.append('</div>')

        # ===== 完成进度总览（统一板块一矩阵管线：系统类型 × 项目 + 中高/低优先级 + 业务测试） =====
        pr = bpc.get('priority_rows', [])
        P.append('<h3 id="bpc-overview" style="margin-top:20px;color:#1a3a5c">📊 完成进度总览（含优先级分层 + 业务测试）</h3>')
        if pr:
            has_trend = bool(trend and trend.get('proj_diff'))
            trend_header = '<th>较上期Δ</th><th>新增完成</th>' if has_trend else ''
            trend_note = ''
            if has_trend:
                trend_note = f'<br><small style="color:#555">📈 点击<strong>项目名</strong>查看多日变化明细；「较上期Δ」「新增完成」对比基准快照：<strong>{trend["base_date"]}</strong>（间隔 {trend["base_interval"]} 天）</small>'
            P.append(f'<div class="alert alert-info">BPC前端按<span style="font-weight:600;color:#1d4ed8">系统类型</span>×<span style="font-weight:600;color:#059669">项目</span>下钻视图，按完成率升序排列；蓝色数字可点击查看全量明细弹窗。{trend_note}</div>')
            P.append('<div class="table-wrap"><table>')
            P.append(f'<tr><th>系统类型</th><th>项目</th><th>总任务</th><th>已完成</th><th>已取消</th><th>整体完成率</th>{trend_header}<th>中高总数</th><th>中高已取消</th><th>中高进行中</th><th>中高已完成</th><th>中高剩余</th><th>中高完成率</th><th>低总数</th><th>低已取消</th><th>低已完成</th><th>低剩余</th><th>低完成率</th><th>测试已完成</th><th>测试剩余</th><th>测试完成率</th></tr>')
            for mi, r in enumerate(pr):
                _render_row(P, r, mi, 'bpc', show_bt=True, trend=trend)
            _append_subtotal_row(P, pr, '📊 合计', is_grand=True, show_bt=True, prefix='bpc', trend=trend)
            P.append('</table></div>')
            _render_modals(P, pr, 'bpc', show_bt=True)
            _render_trend_modals(P, pr, 'bpc', trend)

        # 按负责人分组（对齐批次项目矩阵：完成率升序，差的在前）
        pd_list = bpc.get('person_detail', [])
        if pd_list:
            P.append('<div class="subsection">')
            P.append('<h3 class="collapse-toggle" onclick="toggleCollapse(this)"><span class="arrow">▼</span>按负责人完成进度（完成率升序）</h3>')
            P.append('<div class="collapse-body">')
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th>负责人</th><th>总任务</th><th>已完成</th><th>已取消</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
            for pr in pd_list:
                pc = 'badge-gray' if pr['person'] == '（未分配）' else ''
                P.append(f'<tr><td><span class="badge {pc}">{pr["person"]}</span></td><td>{pr["total"]}</td><td>{pr["done"]}</td><td>{pr["cancelled"]}</td><td><span style="color:#dc2626;font-weight:600">{pr["undone"]}</span></td><td><span class="badge {_rate_badge(pr["comp_rate"])}">{pr["comp_rate"]}%</span></td><td>{pr["days"]}</td></tr>')
            p_t = sum(x['total'] for x in pd_list); p_d = sum(x['done'] for x in pd_list); p_c = sum(x['cancelled'] for x in pd_list); p_u = sum(x['undone'] for x in pd_list); p_dy = sum(x['days'] for x in pd_list)
            p_r = round(p_d / (p_t - p_c) * 100, 1) if (p_t - p_c) > 0 else 0
            P.append(f'<tr style="font-weight:700;background:#f0f5ff"><td><strong>📊 合计</strong></td><td><strong>{p_t}</strong></td><td><strong>{p_d}</strong></td><td>{p_c}</td><td><strong>{p_u}</strong></td><td><span class="badge {_rate_badge(p_r)}"><strong>{p_r}%</strong></span></td><td><strong>{p_dy}</strong></td></tr>')
            P.append('</table></div></div></div>')

        # ===== 维度一：未完成任务 → 推进风险（先进度、看逾期，完成与验收内容放最后） =====
        P.append(f'<h3 id="bpc-risk" style="margin-top:20px;color:#dc2626">🔴 未完成任务（{bpc["undone"]} 条）→ 推进风险</h3>')

        # ===== 2.1 / 2.2 逾期 & 临期 — 延期原因与备注（对齐板块一 2.1/2.2 折叠表格） =====
        bpc_overdue_items = [(item, '🔴逾期') for item in bpc['overdue_list']]
        bpc_near_items = [(item, '🟡临期') for item in bpc['near_due_list']]
        bpc_overdue_items.sort(key=lambda x: -x[0].get('days_diff', 0))
        bpc_near_items.sort(key=lambda x: x[0].get('days_diff', 0))
        bpc_all_risk = bpc_overdue_items + bpc_near_items
        bt_overdue_items = [(item, '🔴逾期') for item in bpc.get('bt_overdue_list', [])]
        bt_near_items = [(item, '🟡临期') for item in bpc.get('bt_near_due_list', [])]
        bt_overdue_items.sort(key=lambda x: -x[0].get('days_diff', 0))
        bt_near_items.sort(key=lambda x: x[0].get('days_diff', 0))
        bpc_bt_all_risk = bt_overdue_items + bt_near_items

        # 2.1 开发逾期 & 临期（折叠表格）
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.1 逾期 & 临期任务 — 开发（{len(bpc_all_risk)}条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        P.append('<div class="table-wrap"><table>')
        P.append('<tr><th>类型</th><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>状态</th><th>FS状态</th><th>业务测试状态</th><th>TS状态</th><th>优先级</th><th>负责人</th><th>计划结束</th><th>进度</th><th>延期原因</th><th>备注</th></tr>')
        for item, tag in bpc_all_risk:
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
        bpc_dev_reason_ok = sum(1 for item, _ in bpc_all_risk if item.get('reason', '（未填写）') not in ['（未填写）', '-', ''])
        bpc_dev_remark_ok = sum(1 for item, _ in bpc_all_risk if item.get('remark', '（无备注）') not in ['（无备注）', '-', ''])
        P.append(f'<div style="margin-top:10px;font-size:13px;color:#666">📌 延期原因填写率: {bpc_dev_reason_ok}/{len(bpc_all_risk)} | 备注填写率: {bpc_dev_remark_ok}/{len(bpc_all_risk)}</div>')
        P.append('</div></div>')

        # 2.2 测试逾期 & 临期（折叠表格）
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.2 逾期 & 临期任务 — 测试（{len(bpc_bt_all_risk)}条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if bpc_bt_all_risk:
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th>类型</th><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>状态</th><th>业务测试状态</th><th>业务测试负责人</th><th>优先级</th><th>负责人</th><th>测试计划结束</th><th>延期原因</th><th>备注</th></tr>')
            for item, tag in bpc_bt_all_risk:
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
            bpc_bt_reason_ok = sum(1 for item, _ in bpc_bt_all_risk if item.get('reason', '（未填写）') not in ['（未填写）', '-', ''])
            bpc_bt_remark_ok = sum(1 for item, _ in bpc_bt_all_risk if item.get('remark', '（无备注）') not in ['（无备注）', '-', ''])
            P.append(f'<div style="margin-top:10px;font-size:13px;color:#666">📌 延期原因填写率: {bpc_bt_reason_ok}/{len(bpc_bt_all_risk)} | 备注填写率: {bpc_bt_remark_ok}/{len(bpc_bt_all_risk)}</div>')
        else:
            P.append('<div class="alert alert-success">✅ 当前没有业务测试逾期的任务。</div>')
        P.append('</div></div>')
        # 2.3 计划缺失（折叠表格：标注开始/结束日期缺失，全量明细）
        pm_list = bpc.get('plan_missing_list', [])
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.3 计划缺失（无计划开始/结束日期）（{len(pm_list)}条 / 无开始 {bpc["no_start_count"]}条 / 无结束 {bpc["no_end_date_count"]}条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if pm_list:
            P.append('<div class="table-wrap" id="bpc-plan-missing"><table>')
            P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>描述</th><th>优先级</th><th>状态</th><th>负责人</th><th>计划开始</th><th>计划结束</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th></tr>')
            for t in pm_list:
                pc = 'badge-red' if t['priority'] == '高' else ('badge-yellow' if t['priority'] == '中' else 'badge-gray')
                fs_cls = _bpc_badge(t.get('fs_status', '-'))
                bt_cls = _bpc_badge(t.get('bt_status', '-'))
                ts_cls = _bpc_badge(t.get('ts_status', '-'))
                s_cell = '<span style="color:#dc2626;font-weight:600">缺失</span>' if not t['start_ok'] else t.get('start', '-')
                e_cell = '<span style="color:#dc2626;font-weight:600">缺失</span>' if not t['end_ok'] else t.get('end', '-')
                desc = t.get('desc', ''); desc_str = desc[:40] + '…' if len(desc) > 40 else desc
                P.append(f'<tr><td style="text-align:left">{t.get("project", "")}</td><td>{t.get("batch", "")}</td><td>{t.get("system", "")}</td><td>{t.get("module", "")}</td><td style="text-align:left;max-width:200px">{t["task"]}</td><td style="text-align:left;font-size:11px;max-width:180px">{desc_str}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["status"]}</td><td>{t["person"]}</td><td>{s_cell}</td><td>{e_cell}</td><td>{t["progress"]}</td><td><span class="badge {fs_cls}">{t.get("fs_status", "-")}</span></td><td><span class="badge {bt_cls}">{t.get("bt_status", "-")}</span></td><td><span class="badge {ts_cls}">{t.get("ts_status", "-")}</span></td></tr>')
            P.append('</table></div>')
        else:
            P.append('<div class="alert alert-success" id="bpc-plan-missing">✅ 当前没有计划缺失的任务。</div>')
        P.append('</div></div>')

        # 2.4 待处理从未启动（折叠表格，全量明细）
        pz_list = bpc.get('pending_zero_list', [])
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.4 待处理从未启动（进度=0%）（{len(pz_list)}条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if pz_list:
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>描述</th><th>优先级</th><th>负责人</th><th>计划结束</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th></tr>')
            for t in pz_list:
                pc = 'badge-red' if t['priority'] == '高' else ('badge-yellow' if t['priority'] == '中' else 'badge-gray')
                fs_cls = _bpc_badge(t.get('fs_status', '-'))
                bt_cls = _bpc_badge(t.get('bt_status', '-'))
                ts_cls = _bpc_badge(t.get('ts_status', '-'))
                desc = t.get('desc', ''); desc_str = desc[:40] + '…' if len(desc) > 40 else desc
                P.append(f'<tr><td style="text-align:left">{t.get("project", "")}</td><td>{t.get("batch", "")}</td><td>{t.get("system", "")}</td><td>{t.get("module", "")}</td><td style="text-align:left;max-width:200px">{t["task"]}</td><td style="text-align:left;font-size:11px;max-width:180px">{desc_str}</td><td><span class="badge {pc}">{t["priority"]}</span></td><td>{t["person"]}</td><td>{t.get("end", "-")}</td><td>{t["progress"]}</td><td><span class="badge {fs_cls}">{t.get("fs_status", "-")}</span></td><td><span class="badge {bt_cls}">{t.get("bt_status", "-")}</span></td><td><span class="badge {ts_cls}">{t.get("ts_status", "-")}</span></td></tr>')
            P.append('</table></div>')
        else:
            P.append('<div class="alert alert-success">✅ 当前没有待处理从未启动的任务。</div>')
        P.append('</div></div>')

        # 2.5 必填字段缺失
        ufc = bpc.get('undone_field_comp', {})
        if ufc:
            bad_fields = [(f, v) for f, v in ufc.items() if v['rate'] < 80]
            bad_fields.sort(key=lambda x: x[1]['rate'])
            if bad_fields:
                um_rows = bpc.get('undone_missing_rows', [])
                P.append('<div class="subsection" id="bpc-field-missing">')
                P.append('<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>2.5 必填字段缺失（填写率 &lt; 80%）</h3>')
                P.append('<div class="collapse-body collapsed">')
                P.append('<div class="table-wrap"><table>')
                P.append('<tr><th>字段</th><th>已填写</th><th>缺失</th><th>填写率</th></tr>')
                for fname, fv in bad_fields:
                    rc = 'badge-red' if fv['rate'] < 50 else 'badge-yellow'
                    P.append(f'<tr><td style="text-align:left">{fname}</td><td>{fv["filled"]}</td><td><span style="color:#dc2626;font-weight:600">{fv["missing"]}</span></td><td><span class="badge {rc}">{fv["rate"]}%</span></td></tr>')
                P.append('</table></div>')
                if um_rows:
                    P.append('<div class="subsection" style="margin-top:8px">')
                    P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>缺失 ≥4 字段的任务明细（{len(um_rows)} 条）</h3>')
                    P.append('<div class="collapse-body collapsed">')
                    P.append('<div class="table-wrap"><table>')
                    P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>缺失数</th><th>缺失字段</th><th>状态</th><th>负责人</th><th>进度</th><th>FS</th><th>业务测试</th></tr>')
                    for ti, r in enumerate(um_rows, 1):
                        mc = 'badge-red' if r['missing_count'] >= 6 else 'badge-yellow'
                        fs_cls = _bpc_badge(r.get('fs_status', '-'))
                        bt_cls = _bpc_badge(r.get('bt_status', '-'))
                        P.append(f'<tr><td>{ti}</td><td style="text-align:left">{r.get("project", "")}</td><td>{r.get("batch", "")}</td><td>{r.get("system", "")}</td><td>{r.get("module", "")}</td><td style="text-align:left;max-width:200px">{r["task"]}</td><td><span class="badge {mc}">{r["missing_count"]}</span></td><td style="text-align:left;font-size:11px">{r["missing_fields"]}</td><td>{r["status"]}</td><td>{r["person"]}</td><td>{r.get("progress", "")}</td><td><span class="badge {fs_cls}">{r.get("fs_status", "-")}</span></td><td><span class="badge {bt_cls}">{r.get("bt_status", "-")}</span></td></tr>')
                    P.append('</table></div></div></div>')
                P.append('</div></div>')

        # ===== 维度二：共性问题 =====
        P.append('<h3 style="margin-top:20px;color:#7c3aed">⚡ 共性问题</h3>')

        anomalies = bpc.get('man_day_anomalies', [])
        anomalies = sorted(anomalies, key=lambda x: -x.get('days', 0)) if anomalies else []
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>3.1 人天异常 ≥10天（{len(anomalies)}条 / 中位数 {bpc.get("man_day_median", "-")}天）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if anomalies:
            P.append('<div class="table-wrap" id="bpc-man-day"><table>')
            P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>人天</th><th>状态</th><th>完成标记</th><th>负责人</th><th>FS</th><th>计划结束</th><th>进度</th></tr>')
            for a in anomalies:
                fs_cls = _bpc_badge(a.get('fs_status', '-'))
                dm = a.get('done_mark', ''); dm_cls = 'badge-green' if dm == '已完成' else 'badge-orange'
                P.append(f'<tr><td style="text-align:left">{a.get("project", "")}</td><td>{a.get("batch", "")}</td><td>{a.get("system", "")}</td><td>{a.get("module", "")}</td><td style="text-align:left;max-width:200px">{a["task"]}</td><td><span class="badge badge-red" style="font-size:13px">{a["days"]}天</span></td><td>{a["status"]}</td><td><span class="badge {dm_cls}">{dm}</span></td><td>{a["person"]}</td><td><span class="badge {fs_cls}">{a.get("fs_status", "-")}</span></td><td>{a.get("end", "-")}</td><td>{a["progress"]}</td></tr>')
            P.append('</table></div>')
        else:
            P.append('<div class="alert alert-success" id="bpc-man-day">✅ 当前没有人天异常（≥10天）的任务。</div>')
        P.append('</div></div>')

        # 3.2 非标准状态（折叠表格）
        ab_list = bpc.get('abnormal_status_list', [])
        ac = bpc.get('abnormal_status_counter', {})
        tags = ' | '.join(f'{k}: {v}条' for k, v in ac.items())
        ab_note = f'（{tags}）' if tags else ''
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>3.2 非标准状态任务{ab_note}（{len(ab_list)}条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if ab_list:
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>状态</th><th>完成标记</th><th>负责人</th><th>计划结束</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th></tr>')
            for a in ab_list:
                fs_cls = _bpc_badge(a.get('fs_status', '-'))
                bt_cls = _bpc_badge(a.get('bt_status', '-'))
                ts_cls = _bpc_badge(a.get('ts_status', '-'))
                dm = a.get('done_mark', ''); dm_cls = 'badge-green' if dm == '已完成' else 'badge-orange'
                P.append(f'<tr><td style="text-align:left">{a.get("project", "")}</td><td>{a.get("batch", "")}</td><td>{a.get("system", "")}</td><td>{a.get("module", "")}</td><td style="text-align:left;max-width:200px">{a["task"]}</td><td><span class="badge badge-yellow">{a["status"]}</span></td><td><span class="badge {dm_cls}">{dm}</span></td><td>{a["person"]}</td><td>{a.get("end", "-")}</td><td>{a["progress"]}</td><td><span class="badge {fs_cls}">{a.get("fs_status", "-")}</span></td><td><span class="badge {bt_cls}">{a.get("bt_status", "-")}</span></td><td><span class="badge {ts_cls}">{a.get("ts_status", "-")}</span></td></tr>')
            P.append('</table></div>')
        else:
            P.append('<div class="alert alert-success">✅ 当前没有非标准状态的任务。</div>')
        P.append('</div></div>')

        # 3.3 未分配负责人（折叠表格）
        ua_list = bpc.get('unassigned_list', [])
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>3.3 未分配负责人（{len(ua_list)}条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if ua_list:
            P.append('<div class="table-wrap" id="bpc-unassigned"><table>')
            P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务</th><th>状态</th><th>完成标记</th><th>进度</th><th>FS</th><th>业务测试</th><th>TS</th><th>计划结束</th></tr>')
            for u in ua_list:
                fs_cls = _bpc_badge(u.get('fs_status', '-'))
                bt_cls = _bpc_badge(u.get('bt_status', '-'))
                ts_cls = _bpc_badge(u.get('ts_status', '-'))
                dm = u.get('done_mark', ''); dm_cls = 'badge-green' if dm == '已完成' else 'badge-orange'
                P.append(f'<tr><td style="text-align:left">{u.get("project", "")}</td><td>{u.get("batch", "")}</td><td>{u.get("system", "")}</td><td>{u.get("module", "")}</td><td style="text-align:left;max-width:200px">{u["task"]}</td><td>{u["status"]}</td><td><span class="badge {dm_cls}">{dm}</span></td><td>{u["progress"]}</td><td><span class="badge {fs_cls}">{u.get("fs_status", "-")}</span></td><td><span class="badge {bt_cls}">{u.get("bt_status", "-")}</span></td><td><span class="badge {ts_cls}">{u.get("ts_status", "-")}</span></td><td>{u.get("end", "-")}</td></tr>')
            P.append('</table></div>')
        else:
            P.append('<div class="alert alert-success" id="bpc-unassigned">✅ 当前没有未分配负责人的任务。</div>')
        P.append('</div></div>')

        # ===== 维度三：已完成任务 → 验收就绪（最后展示：先看进度与逾期，再看完成内容与验收材料） =====
        P.append(f'<h3 id="bpc-acceptance" style="margin-top:20px;color:#16a34a">✅ 已完成任务（{bpc["done"]} 条）→ 验收就绪</h3>')

        af = bpc.get('acceptance_fields', {})
        if af:
            P.append('<div class="subsection" id="bpc-acceptance-fields">')
            P.append('<h3 class="collapse-toggle" onclick="toggleCollapse(this)"><span class="arrow">▼</span>验收材料填写率</h3>')
            P.append('<div class="collapse-body">')
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th>验收字段</th><th>已填写</th><th>缺失</th><th>填写率</th></tr>')
            for fname, fv in sorted(af.items(), key=lambda x: x[1]['rate']):
                rc = 'badge-red' if fv['rate'] < 50 else ('badge-yellow' if fv['rate'] < 80 else 'badge-green')
                P.append(f'<tr><td style="text-align:left">{fname}</td><td>{fv["filled"]}</td><td><span style="color:#dc2626;font-weight:600">{fv["missing"]}</span></td><td><span class="badge {rc}">{fv["rate"]}%</span></td></tr>')
            P.append('</table></div></div></div>')

        ai = bpc.get('acceptance_issues', [])
        P.append('<div class="subsection">')
        P.append(f'<h3 class="collapse-toggle collapsed" onclick="toggleCollapse(this)"><span class="arrow">▼</span>验收材料不全明细（{len(ai)}条 / 已完成 {bpc["done"]} 条）</h3>')
        P.append('<div class="collapse-body collapsed">')
        if ai:
            P.append('<div class="table-wrap"><table>')
            P.append('<tr><th>#</th><th>模块</th><th>任务</th><th>描述</th><th>优先级</th><th>缺失材料</th><th>缺失数</th><th>负责人</th><th>BT状态</th><th>计划结束</th></tr>')
            for i, a in enumerate(ai, 1):
                mc = 'badge-red' if a['missing_count'] >= 5 else 'badge-yellow'
                pc = 'badge-red' if a.get('priority') == '高' else ('badge-yellow' if a.get('priority') == '中' else 'badge-gray')
                bt = a.get('bt_status', '-')
                bt_cls = _bpc_badge(bt)
                desc = a.get('desc', ''); desc_str = desc[:40] + '…' if len(desc) > 40 else desc
                P.append(f'<tr><td>{i}</td><td>{a.get("module", "")}</td><td style="text-align:left;max-width:200px">{a["task"]}</td><td style="text-align:left;font-size:11px;max-width:180px">{desc_str}</td><td><span class="badge {pc}">{a.get("priority", "")}</span></td><td style="text-align:left;font-size:11px">{a["missing"]}</td><td><span class="badge {mc}">{a["missing_count"]}</span></td><td>{a["person"]}</td><td><span class="badge {bt_cls}">{bt}</span></td><td>{a["end"]}</td></tr>')
            P.append('</table></div>')
        else:
            P.append('<div class="alert alert-success">✅ 已完成任务验收材料均已齐全。</div>')
        P.append('</div></div>')

        P.append('</div>')  # close BPC section

    P.append(f'<div class="footer"><p>1455项目 PMO监控分析报告 | 自动生成于 {d["generated_at"]} | 数据截止 {d["report_date"]}</p><p>逾期判断：结束日期 < {d["report_date"]} 且未完成 | 临期：{d["report_date"]}后7天内到期</p></div></div>')

    P.append('<script>\n' + modal_js + collapse_js + '\n</script></body></html>')
    html = '\n'.join(P)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
