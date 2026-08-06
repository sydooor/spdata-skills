"""验证 quality_renderer.py 是否正确生成 8 类检查报告"""
import sys, os, glob

os.chdir(r'C:\Users\zhahuang\Documents\Customer-Data\国电投\开发任务管理')
sys.path.insert(0, r'.qoder\skills\pmo-analysis-skill\scripts')

# 清理缓存
import importlib
for mod in ['pmo_analyzer', 'quality_renderer', 'data_quality', 'stats_computer', 'html_renderer', 'data_loader', 'config']:
    if mod in sys.modules:
        del sys.modules[mod]

files = sorted([f for f in glob.glob('data/*2026_7_26*.xlsx') if not os.path.basename(f).startswith('~$')])
print(f'Input file: {files[0]}')

sys.argv = ['pmo_analyzer.py', files[0]]
from pmo_analyzer import main
main()

# Verify output
out_files = glob.glob('outputs/*20260726*.html')
print(f'\n=== Output files ===')
for f in sorted(out_files):
    size = os.path.getsize(f)
    print(f'  {os.path.basename(f)}: {size} bytes')

# Quick check of quality report content
qfile = [f for f in out_files if '质量' in f][0]
with open(qfile, 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('8 类检查规则', '1. 8-class section header'),
    ('8 类检查规则', '2. 8-class alert text'),
    ('阶段流程异常', '3. phase_flow in KPI cards'),
    ('必填字段缺失', '4. required_field in KPI cards'),
    ('阶段流程', '5. phase_flow in by_batch_system'),
    ('必填缺失', '6. required_field in by_batch_system'),
    ('阶段流程', '7. phase_flow in by_project'),
    ('必填缺失', '8. required_field in by_project'),
    ('必填字段缺失明细', '9. per-field breakdown section'),
    ('缺失率', '10. missing_rate column'),
    ('受影响项目数', '11. num_projects column'),
    ('各字段受影响项目分布', '12. per-field project breakout'),
    ('8 类违规', '13. Section 4 - 8 class'),
]

print(f'\n=== Content verification ===')
for keyword, desc in checks:
    found = keyword in content
    status = '✅' if found else '❌'
    print(f'  {status} {desc}: "{keyword}"')

print(f'\nDone! Check the HTML files in outputs/')
