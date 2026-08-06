#!/usr/bin/env python3
"""
PMO 项目监控分析工具 — 国电投1455项目
支持输出 HTML 报告，含数据质量检查。

用法:
  python pmo_analyzer.py <输入.xlsx>                     # 生成 HTML 报告
  python pmo_analyzer.py <输入.xlsx> -o report.html -d 2026/7/22
"""

import sys, os, argparse
import pandas as pd

from data_loader import load_and_clean
from stats_computer import compute_all_stats
from html_renderer import generate_html
from quality_renderer import generate_quality_html


def main():
    parser = argparse.ArgumentParser(description='PMO项目监控分析工具')
    parser.add_argument('input', help='输入Excel文件路径')
    parser.add_argument('-o', '--output', default=None, help='输出HTML文件路径')
    parser.add_argument('-d', '--date', default=None, help='报告日期, 如 2026/7/22 (默认取数据中最晚结束日期)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'❌ 文件不存在: {args.input}')
        sys.exit(1)

    print(f'📊 正在分析: {args.input}')
    df = load_and_clean(args.input)
    print(f'   数据: {len(df)}行, 批次: {df["批次"].nunique()}, JAVA: {len(df[df["系统类型"]=="JAVA-专业系统"])}, SAP: {len(df[df["系统类型"]=="SAP"])}')

    # 报告日期
    report_date = args.date if args.date else pd.Timestamp.now().strftime('%Y/%m/%d')
    print(f'   报告日期: {report_date}')

    # 输出路径
    if args.output is None:
        base = os.path.splitext(os.path.basename(args.input))[0]
        date_str = pd.Timestamp(report_date).strftime('%Y%m%d')
        os.makedirs('outputs', exist_ok=True)
        args.output = os.path.join('outputs', f'{base}_PMO监控分析报告_{date_str}.html')

    # 统计计算（含数据质量维度）
    print('   计算统计指标（含数据质量检查）...')
    data = compute_all_stats(df, report_date)

    # 质量维度摘要
    quality = data.get('quality', {})
    total_issues = quality.get('total_issues', 0)
    print(f'   质量问题: {total_issues} 项')
    if quality.get('by_batch'):
        top_batch = quality['by_batch'][0]
        print(f'   质量最差批次: {top_batch["batch"]} ({top_batch["total"]}项)')
    if quality.get('by_project'):
        top_proj = quality['by_project'][0]
        print(f'   质量问题最多项目: {top_proj["project"]} ({top_proj["total"]}项)')
    print(f'   逾期: {data["kpi"]["overdue"]}条, 临期: {data["kpi"]["near_due"]}条, 未完成: {data["kpi"]["undone"]}条')

    # 生成 HTML 报告（主报告 + 质量专项报告）
    print('   生成HTML报告...')
    generate_html(data, args.output)
    print(f'✅ 主报告: {args.output}')

    quality_output = args.output.replace('_PMO监控分析报告_', '_数据质量专项报告_')
    generate_quality_html(data, quality_output, main_report_filename=os.path.basename(args.output))
    print(f'✅ 质量专项报告: {quality_output}')


if __name__ == '__main__':
    main()
