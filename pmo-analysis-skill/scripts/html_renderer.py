"""PMO 项目监控分析 — HTML 报告渲染"""

import json
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
.dim-system{background:#ede9fe;color:#6b21a8}"""


# ============================================================
# 风险区域（逾期/临期）
# ============================================================
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
        pc = 'badge-red' if item['priority'] == '高' else ('badge-yellow' if item['priority'] == '中' else 'badge-gray')
        P.append(f'<tr><td><strong>{i + 1}</strong></td><td style="text-align:left">{item["project"]}</td><td>{item["batch"]}</td><td>{item["system"]}</td><td>{item["module"]}</td><td style="text-align:left;max-width:250px">{item["task"]}</td><td>{item["type"]}</td><td><span class="badge {pc}">{item["priority"]}</span></td><td>{item["status"]}</td><td>{item["person"]}</td><td>{item["end"]} {diff_str}</td><td>{item["progress"]}</td><td style="text-align:left;font-size:11px">{item["reason"]}</td></tr>')
    P.append('</table></div>')
    proj_c = Counter(item['project'] for item in items)
    batch_c = Counter(item['batch'] for item in items)
    sys_c = Counter(item['system'] for item in items)
    P.append('<div style="margin-top:10px;font-size:13px;color:#666">')
    P.append(f'📌 涉及项目: {", ".join(f"{k}({v})" for k, v in proj_c.most_common())} | ')
    P.append(f'批次: {", ".join(f"{k}({v})" for k, v in batch_c.most_common())} | ')
    P.append(f'系统: {", ".join(f"{k}({v})" for k, v in sys_c.most_common())} | ')
    reason_filled = sum(1 for item in items if item['reason'] not in ['（未填写）', '-', ''])
    P.append(f'延期原因填写: {reason_filled}/{len(items)}')
    P.append('</div></div>')


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

    # ===== 数据质量概览（多维度） =====
    if d.get('quality'):
        q = d['quality']
        # 兼容新旧格式
        is_rich = 'summary' in q
        summary = q['summary'] if is_rich else q
        total_issues = q.get('total_issues', sum(v['count'] for v in summary.values()))

        P.append('<div class="section" style="border-left:4px solid #7c3aed"><h2>数据质量检查 — 多维度分析</h2>')
        if total_issues == 0:
            P.append('<div class="alert alert-success">✅ 数据质量检查全部通过</div>')
        else:
            P.append(f'<div class="alert alert-warn">⚠️ 发现 <strong>{total_issues}</strong> 项数据质量问题，覆盖 <strong>6</strong> 类检查规则</div>')

            # ----- 质量KPI卡片 -----
            P.append('<div class="kpi-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">')
            issue_labels = {
                'placeholder_violations': '占位符违规',
                'status_progress_mismatch': '状态-进度不一致',
                'date_format_issues': '日期格式异常',
                'task_cycle_exceeded': '任务周期超标',
                'conditional_missing': '条件必填缺失',
                'system_field_missing': '系统特有字段缺失',
            }
            for key, label in issue_labels.items():
                if key in summary:
                    count = summary[key]['count']
                    cls = 'green' if count == 0 else 'red'
                    P.append(f'<div class="kpi-card {cls}"><div class="label">{label}</div><div class="value">{count}</div></div>')
            P.append('</div>')

            # ----- 质量分类柱状图 -----
            P.append('<div class="chart-row"><div class="chart-box" style="grid-column:1/-1"><h3>各类质量问题分布</h3><canvas id="qualityBarChart"></canvas></div></div>')

            if is_rich:
                # ----- 批次×系统类型 质量分布 -----
                if q.get('by_batch_system'):
                    P.append('<h3>批次 × 系统类型 质量问题分布</h3>')
                    P.append('<div class="table-wrap"><table>')
                    P.append('<tr><th>批次</th><th>系统类型</th><th>问题总数</th><th>占位符</th><th>状态进度</th><th>日期格式</th><th>周期超标</th><th>条件必填</th><th>系统字段</th></tr>')
                    for r in q['by_batch_system']:
                        total = r['total']
                        cls = 'badge-red' if total > 100 else ('badge-yellow' if total > 50 else 'badge-green')
                        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["system"]}</td><td><span class="badge {cls}">{total}</span></td><td>{r.get("placeholder_violations",0)}</td><td>{r.get("status_progress_mismatch",0)}</td><td>{r.get("date_format_issues",0)}</td><td>{r.get("task_cycle_exceeded",0)}</td><td>{r.get("conditional_missing",0)}</td><td>{r.get("system_field_missing",0)}</td></tr>')
                    P.append('</table></div>')

                # ----- 项目质量问题排名 -----
                if q.get('by_project'):
                    top_proj = q['by_project'][:15]
                    P.append(f'<h3>项目质量问题排名（Top {len(top_proj)}）</h3>')
                    P.append('<div class="table-wrap"><table>')
                    P.append('<tr><th>排名</th><th>项目</th><th>问题总数</th><th>占位符</th><th>状态进度</th><th>日期格式</th><th>周期超标</th><th>条件必填</th><th>系统字段</th></tr>')
                    for i, r in enumerate(top_proj):
                        total = r['total']
                        cls = 'badge-red' if total > 100 else ('badge-yellow' if total > 50 else 'badge-green')
                        P.append(f'<tr><td><strong>{i+1}</strong></td><td style="text-align:left">{r["project"]}</td><td><span class="badge {cls}">{total}</span></td><td>{r.get("placeholder_violations",0)}</td><td>{r.get("status_progress_mismatch",0)}</td><td>{r.get("date_format_issues",0)}</td><td>{r.get("task_cycle_exceeded",0)}</td><td>{r.get("conditional_missing",0)}</td><td>{r.get("system_field_missing",0)}</td></tr>')
                    P.append('</table></div>')

                # ----- 问题最多的Top任务 -----
                if q.get('top_tasks'):
                    top_ts = q['top_tasks'][:20]
                    P.append(f'<h3>质量问题最多的任务（Top {len(top_ts)}）</h3>')
                    P.append('<div class="table-wrap"><table>')
                    P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>任务名称</th><th>问题数</th></tr>')
                    for i, t in enumerate(top_ts):
                        ic = 'badge-red' if t['issues'] >= 3 else 'badge-yellow'
                        P.append(f'<tr><td>{i+1}</td><td style="text-align:left">{t["project"]}</td><td>{t["batch"]}</td><td>{t["system"]}</td><td style="text-align:left;max-width:300px">{t["task"]}</td><td><span class="badge {ic}">{t["issues"]}</span></td></tr>')
                    P.append('</table></div>')
        P.append('</div>')

    # ===== 逾期任务 =====
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
        rc = 'badge-green' if r['rate'] >= 90 else ('badge-yellow' if r['rate'] >= 70 else 'badge-red')
        bc = 'badge-blue' if r['batch'] != '未标注批次' else 'badge-gray'
        sc = 'badge-purple' if r['system'] == 'JAVA-专业系统' else 'badge-blue'
        od_str = f'<span class="badge badge-red">{r["overdue"]}</span>' if r['overdue'] > 0 else '-'
        nd_str = f'<span class="badge badge-yellow">{r["near_due"]}</span>' if r['near_due'] > 0 else '-'
        P.append(f'<tr><td>{i + 1}</td><td style="text-align:left;font-weight:600">{r["project"]}</td><td><span class="badge {bc}">{r["batch"]}</span></td><td><span class="badge {sc}">{r["system"]}</span></td><td>{r["total"]}</td><td>{r["done"]}</td><td><span class="badge {rc}">{r["rate"]}%</span></td><td>{r["days"]}</td><td>{od_str}</td><td>{nd_str}</td></tr>')
    P.append('</table></div></div>')

    # ===== 二、批次 × 系统类型 总览 =====
    P.append('<div class="section"><h2>二、批次 × 系统类型 总览</h2>')
    P.append('<div class="chart-row"><div class="chart-box"><h3>各批次任务分布</h3><canvas id="batchBarChart"></canvas></div>')
    P.append('<div class="chart-box"><h3>系统类型分布</h3><canvas id="sysPieChart"></canvas></div></div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>系统类型</th><th>总任务</th><th>已完成</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
    for r in d['batch_system']:
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 三、未完成任务明细 =====
    undone = d['undone_detail']
    P.append(f'<div class="section" style="border-left:4px solid #dc2626"><h2>三、未完成任务明细（{len(undone)}条）— 项目 × 批次 × 系统类型</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>模块</th><th>任务名称</th><th>类型</th><th>优先级</th><th>状态</th><th>负责人</th><th>进度</th></tr>')
    for r in undone:
        pc = 'badge-red' if r['priority'] == '高' else ('badge-yellow' if r['priority'] == '中' else 'badge-gray')
        P.append(f'<tr><td style="text-align:left">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["module"]}</td><td style="text-align:left;max-width:250px">{r["task"]}</td><td>{r["type"]}</td><td><span class="badge {pc}">{r["priority"]}</span></td><td>{r["status"]}</td><td>{r["person"]}</td><td>{r["progress"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 四、供应商×批次×系统类型 =====
    P.append('<div class="section"><h2>四、供应商团队绩效 — 批次 × 系统类型</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>供应商</th><th>批次</th><th>系统</th><th>总任务</th><th>已完成</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
    for r in d['team_detail']:
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{r["team"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td>{r["done"]}</td><td>{r["undone"]}</td><td><span class="badge {rc}">{r["comp_rate"]}%</span></td><td>{r["days"]}</td></tr>')
    P.append('</table></div></div>')

    # ===== 五、模块×批次×系统类型 =====
    P.append('<div class="section"><h2>五、模块完成率明细 — 批次 × 系统类型</h2>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>模块</th><th>批次</th><th>系统</th><th>总任务</th><th>已完成</th><th>未完成</th><th>完成率</th><th>人天</th></tr>')
    for r in d['module_detail']:
        rc = 'badge-green' if r['comp_rate'] >= 90 else ('badge-yellow' if r['comp_rate'] >= 70 else 'badge-red')
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
        rc = 'badge-green' if f['rate'] >= 95 else ('badge-yellow' if f['rate'] >= 80 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{f["field"]}</td><td>{f["filled"]}</td><td><span class="badge badge-red">{f["missing"]}</span></td><td><span class="badge {rc}">{f["rate"]}%</span></td></tr>')
    P.append('</table></div>')
    P.append('<h3>7.2 批次×系统类型 完整度</h3><div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>系统</th><th>总任务</th><th>平均完整率</th><th>100%完整记录</th><th>100%占比</th></tr>')
    for r in d['batch_system_field_comp']:
        rc = 'badge-green' if r['avg_rate'] >= 95 else ('badge-yellow' if r['avg_rate'] >= 80 else 'badge-red')
        P.append(f'<tr><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total"]}</td><td><span class="badge {rc}">{r["avg_rate"]}%</span></td><td>{r["perfect"]}</td><td>{r["perfect_rate"]}%</td></tr>')
    P.append('</table></div>')
    if d['undone_field_issues']:
        P.append('<h3>7.3 未完成任务必填字段缺失 Top 50</h3><div class="table-wrap"><table>')
        P.append('<tr><th>#</th><th>项目</th><th>批次</th><th>系统</th><th>任务</th><th>状态</th><th>负责人</th><th>缺失数</th><th>缺失字段</th></tr>')
        for i, iss in enumerate(d['undone_field_issues']):
            mc = 'badge-red' if iss['missing_count'] >= 5 else 'badge-yellow'
            P.append(f'<tr><td>{i + 1}</td><td style="text-align:left">{iss["project"]}</td><td>{iss["batch"]}</td><td>{iss["system"]}</td><td style="text-align:left;max-width:250px">{iss["task"]}</td><td>{iss["status"]}</td><td>{iss["person"]}</td><td><span class="badge {mc}">{iss["missing_count"]}</span></td><td style="text-align:left;font-size:11px">{iss["missing_fields"]}</td></tr>')
        P.append('</table></div>')
    P.append('</div>')

    # ===== 八、批次上线时间节点 =====
    P.append('<div class="section" style="border-left:4px solid #7c3aed"><h2>八、批次上线时间节点 & 开发截止预警</h2>')
    P.append('<div class="alert alert-info">上线时间：A批次 7/31、B批次 8/30、C批次 10/30。开发任务需提前1个月完成。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>批次</th><th>上线日期</th><th>开发截止</th><th>距截止</th><th>总任务</th><th>已完成</th><th>完成率</th><th>超截止未完成</th><th>已完成但超截止</th><th>状态</th></tr>')
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
        P.append(f'<tr><td><strong>{r["batch"]}</strong></td><td>{r["go_live"]}</td><td style="font-weight:600">{r["dev_deadline"]}</td><td>{dl_str}</td><td>{r["total"]}</td><td>{r["done"]}</td><td><span class="badge {rc}">{r["done_rate"]}%</span></td><td>{od_str}</td><td>{r["done_late"]}</td><td>{st_str}</td></tr>')
    P.append('</table></div></div>')

    # ===== 九、已完成任务验收就绪分析 =====
    P.append('<div class="section" style="border-left:4px solid #16a34a"><h2>九、已完成任务验收就绪分析 — 测试报告 & 业务测试</h2>')
    P.append('<div class="alert alert-info">验收需关注：业务测试状态、系统测试报告、集成测试报告、回归测试报告。</div>')

    P.append('<h3>9.1 各项目验收就绪汇总（项目×批次×系统）</h3>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>项目</th><th>批次</th><th>系统</th><th>已完成</th><th>业务测试完成</th><th>系统测试✅</th><th>集成测试✅</th><th>回归测试✅</th><th>全部就绪</th><th>就绪率</th></tr>')
    for r in d['acc_summary']:
        rc = 'badge-green' if r['ready_rate'] >= 80 else ('badge-yellow' if r['ready_rate'] >= 50 else 'badge-red')
        P.append(f'<tr><td style="text-align:left">{r["project"]}</td><td>{r["batch"]}</td><td>{r["system"]}</td><td>{r["total_done"]}</td><td>{r["bt_complete"]}</td><td>{r["sys_test_ok"]}</td><td>{r["integ_test_ok"]}</td><td>{r["regr_test_ok"]}</td><td>{r["all_ready"]}</td><td><span class="badge {rc}">{r["ready_rate"]}%</span></td></tr>')
    P.append('</table></div>')

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
        P.append(f'<tr><td colspan="11" style="color:#666">... 还有 {len(acc_incomplete) - 100} 条</td></tr>')
    P.append('</table></div></div>')

    # ===== 十、延期/临期任务 — 延期原因 & 备注 =====
    P.append('<div class="section" style="border-left:4px solid #dc2626"><h2>十、逾期 & 临期任务 — 延期原因与备注</h2>')
    P.append('<div class="alert alert-danger">以下为逾期+临期任务，重点关注延期原因是否已填写、备注是否有说明。</div>')
    P.append('<div class="table-wrap"><table>')
    P.append('<tr><th>类型</th><th>项目</th><th>批次</th><th>系统</th><th>任务</th><th>状态</th><th>负责人</th><th>计划结束</th><th>进度</th><th>延期原因</th><th>备注</th></tr>')
    all_risk = [(item, '🔴逾期') for item in d['overdue_list']] + [(item, '🟡临期') for item in d['near_due_list']]
    for item, tag in all_risk:
        reason = item.get('reason', '（未填写）')
        remark = item.get('remark', '（无备注）')
        reason_cls = 'color:#dc2626;font-weight:600' if reason == '（未填写）' else ''
        remark_cls = 'color:#9ca3af' if remark == '（无备注）' else ''
        diff = item.get('days_diff', 0)
        if item.get('tag') == '逾期':
            diff_str = f'+{diff}天'
        else:
            diff_str = f'{diff}天'
        P.append(f'<tr><td>{tag}</td><td style="text-align:left">{item["project"]}</td><td>{item["batch"]}</td><td>{item["system"]}</td><td style="text-align:left;max-width:200px">{item["task"]}</td><td>{item["status"]}</td><td>{item["person"]}</td><td>{item["end"]} ({diff_str})</td><td>{item["progress"]}</td><td style="text-align:left;font-size:11px;{reason_cls}">{reason}</td><td style="text-align:left;font-size:11px;{remark_cls}">{remark}</td></tr>')
    P.append('</table></div>')
    reason_ok = sum(1 for item, _ in all_risk if item.get('reason', '（未填写）') not in ['（未填写）', '-', ''])
    remark_ok = sum(1 for item, _ in all_risk if item.get('remark', '（无备注）') not in ['（无备注）', '-', ''])
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

    # Quality chart data
    quality_labels = json.dumps(['占位符违规', '状态进度不一致', '日期格式异常', '任务周期超标', '条件必填缺失', '系统字段缺失'])
    if d.get('quality'):
        q = d['quality']
        is_rich = 'summary' in q
        sq = q['summary'] if is_rich else q
        quality_counts = json.dumps([
            sq.get('placeholder_violations', {}).get('count', 0) if isinstance(sq.get('placeholder_violations', {}), dict) else 0,
            sq.get('status_progress_mismatch', {}).get('count', 0) if isinstance(sq.get('status_progress_mismatch', {}), dict) else 0,
            sq.get('date_format_issues', {}).get('count', 0) if isinstance(sq.get('date_format_issues', {}), dict) else 0,
            sq.get('task_cycle_exceeded', {}).get('count', 0) if isinstance(sq.get('task_cycle_exceeded', {}), dict) else 0,
            sq.get('conditional_missing', {}).get('count', 0) if isinstance(sq.get('conditional_missing', {}), dict) else 0,
            sq.get('system_field_missing', {}).get('count', 0) if isinstance(sq.get('system_field_missing', {}), dict) else 0,
        ])
    else:
        quality_counts = json.dumps([0, 0, 0, 0, 0, 0])

    P.append(f'''<script>
new Chart(document.getElementById('batchBarChart'),{{type:'bar',data:{{labels:{batch_labels},datasets:[{{label:'已完成',data:{batch_done},backgroundColor:'#16a34a'}},{{label:'未完成',data:{batch_undone},backgroundColor:'#ef4444'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{stacked:true}},y:{{stacked:true}}}}}}}});
new Chart(document.getElementById('sysPieChart'),{{type:'doughnut',data:{{labels:{sys_labels},datasets:[{{data:{sys_totals},backgroundColor:['#7c3aed','#2563eb']}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('stageAllChart'),{{type:'bar',data:{{labels:{stage_labels},datasets:[{{label:'完成率(%)',data:{stage_all},backgroundColor:'#2563eb'}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{min:0,max:100}}}}}}}});
new Chart(document.getElementById('stageDoneChart'),{{type:'bar',data:{{labels:{stage_labels},datasets:[{{label:'已完成任务中',data:{stage_done},backgroundColor:'#16a34a'}},{{label:'未完成任务中',data:{stage_undone},backgroundColor:'#ef4444'}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{min:0,max:100}}}}}}}});
new Chart(document.getElementById('qualityBarChart'),{{type:'bar',data:{{labels:{quality_labels},datasets:[{{label:'问题数量',data:{quality_counts},backgroundColor:['#ef4444','#f97316','#eab308','#22c55e','#06b6d4','#8b5cf6']}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true}}}}}}}});
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
