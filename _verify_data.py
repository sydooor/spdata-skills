"""交叉验证: 系统×批次完成率数据准确性 - 写入文件避免终端编码问题"""
import glob, sys, os
os.chdir(r'C:\Users\zhahuang\Documents\Customer-Data\国电投\开发任务管理')
sys.path.insert(0, 'pmo-analysis-skill/scripts')
from data_loader import load_data
from stats_computer import compute_system_batch_priority, compute_kpi, compute_risk
from config import BATCHES, SYSTEM_TYPES
import pandas as pd

OUT = open('_verify_result.txt', 'w', encoding='utf-8')
def p(s=''):
    OUT.write(s + '\n')
    print(s)

report_date = pd.Timestamp('2026/7/22')
df = load_data(glob.glob('data/*2026_7_22*')[0])

p('=== 1. 原始数据总览 ===')
p(f'总行数: {len(df)}')
p(f'SAP: {len(df[df["系统类型"]=="SAP"])}, JAVA: {len(df[df["系统类型"]=="JAVA-专业系统"])}')
total_done = len(df[df['完成标记']=='已完成'])
p(f'已完成: {total_done}, 未完成: {len(df[df["完成标记"]=="未完成"])}')
p(f'整体完成率: {round(total_done/len(df)*100,1)}%')

p('')
p('=== 2. 系统 x 批次: 函数输出 vs 手动计算 ===')
result = compute_system_batch_priority(df)
all_match = True
for r in result:
    st, batch = r['system'], r['batch']
    sub = df[(df['系统类型']==st) & (df['批次']==batch)]
    manual_total = len(sub)
    manual_done = len(sub[sub['完成标记']=='已完成'])
    manual_rate = round(manual_done/manual_total*100, 1) if manual_total>0 else 0
    mh = sub[sub['优先级'].isin(['高','中'])]
    manual_mh_total = len(mh)
    manual_mh_done = len(mh[mh['完成标记']=='已完成'])
    manual_mh_rate = round(manual_mh_done/manual_mh_total*100, 1) if manual_mh_total>0 else 0
    low = sub[sub['优先级']=='低']
    manual_l_total = len(low)
    manual_l_done = len(low[low['完成标记']=='已完成'])
    manual_l_rate = round(manual_l_done/manual_l_total*100, 1) if manual_l_total>0 else 0
    manual_days = int(sub['人天数值'].sum())

    ok = (manual_total == r['total'] and manual_done == r['done'] and manual_rate == r['comp_rate']
          and manual_mh_total == r['mh_total'] and manual_mh_done == r['mh_done'] and manual_mh_rate == r['mh_rate']
          and manual_l_total == r['l_total'] and manual_l_done == r['l_done'] and manual_l_rate == r['l_rate']
          and manual_days == r['days'])
    if not ok:
        all_match = False
        p(f'  [MISMATCH] {st} {batch}:')
        p(f'    total: {r["total"]} vs {manual_total}')
        p(f'    done:  {r["done"]} vs {manual_done}')
        p(f'    rate:  {r["comp_rate"]} vs {manual_rate}')
        p(f'    mh_t:  {r["mh_total"]} vs {manual_mh_total}')
        p(f'    mh_d:  {r["mh_done"]} vs {manual_mh_done}')
        p(f'    mh_r:  {r["mh_rate"]} vs {manual_mh_rate}')
        p(f'    l_t:   {r["l_total"]} vs {manual_l_total}')
        p(f'    l_d:   {r["l_done"]} vs {manual_l_done}')
        p(f'    l_r:   {r["l_rate"]} vs {manual_l_rate}')
        p(f'    days:  {r["days"]} vs {manual_days}')
    else:
        p(f'  [OK] {st} {batch}: total={r["total"]} done={r["done"]} rate={r["comp_rate"]}% mh_rate={r["mh_rate"]}% l_rate={r["l_rate"]}% days={r["days"]}')

p('')
p('=== 3. 汇总行交叉验证 ===')
total_all = sum(r['total'] for r in result)
done_all = sum(r['done'] for r in result)
mh_total_all = sum(r['mh_total'] for r in result)
mh_done_all = sum(r['mh_done'] for r in result)
l_total_all = sum(r['l_total'] for r in result)
l_done_all = sum(r['l_done'] for r in result)
p(f'各组合计: total={total_all} done={done_all} rate={round(done_all/total_all*100,1)}%')
p(f'中高合计: mh_total={mh_total_all} mh_done={mh_done_all} mh_rate={round(mh_done_all/mh_total_all*100,1)}%')
p(f'低优合计: l_total={l_total_all} l_done={l_done_all} l_rate={round(l_done_all/l_total_all*100,1)}%')

# KPI交叉校验
kpi = compute_kpi(df, *compute_risk(df, report_date))
kpi_match = (kpi['total'] == total_all and kpi['done'] == done_all)
p('')
p(f'KPI校验: total={kpi["total"]}({total_all}) done={kpi["done"]}({done_all}) rate={kpi["comp_rate"]}%({round(done_all/total_all*100,1)}%) -> {"PASS" if kpi_match else "FAIL"}')

# 优先级全局校验
mh_manual = len(df[df['优先级'].isin(['高','中'])])
l_manual = len(df[df['优先级'] == '低'])
pri_match = (mh_manual == mh_total_all and l_manual == l_total_all)
p(f'优先级全局: 中高={mh_manual}({mh_total_all}) 低={l_manual}({l_total_all}) -> {"PASS" if pri_match else "FAIL"}')

# 行数校验
sum_check = (total_all == len(df))
p(f'行数校验: {total_all} vs {len(df)} -> {"PASS" if sum_check else "FAIL"}')

p('')
p('=== 最终结论 ===')
if all_match and kpi_match and pri_match and sum_check:
    p('ALL CHECKS PASSED - 数据准确无误。')
else:
    p('存在数据不一致，请检查!')

OUT.close()
