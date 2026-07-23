"""临时脚本：检查数据文件和模板文件结构 v2"""
import pandas as pd
import os, glob

base = r'C:\Users\zhahuang\Documents\Customer-Data\国电投\开发任务管理'

# 1. 模板文件
template = os.path.join(base, '1455推广_开发任务跟踪模板_V1.0.xlsx')
print('=' * 60)
print('【模板文件】1455推广_开发任务跟踪模板_V1.0.xlsx')
print('=' * 60)
df_t = pd.read_excel(template, sheet_name=0)
print(f'行数: {len(df_t)}, 列数: {len(df_t.columns)}')
print(f'列名 ({len(df_t.columns)}个):')
for i, c in enumerate(df_t.columns, 1):
    print(f'  {i:2d}. {c}')

# 2. 实际数据文件 (用glob避免引号问题)
xlsx_files = glob.glob(os.path.join(base, '项目监控*.xlsx'))
print(f'\n找到数据文件: {xlsx_files}')
if xlsx_files:
    data_file = xlsx_files[0]
    print('\n' + '=' * 60)
    print(f'【实际数据】{os.path.basename(data_file)}')
    print('=' * 60)
    df = pd.read_excel(data_file, sheet_name=0)
    print(f'行数: {len(df)}, 列数: {len(df.columns)}')
    print(f'\n列名 ({len(df.columns)}个):')
    for i, c in enumerate(df.columns, 1):
        print(f'  {i:2d}. {c}')

    print(f'\n状态分布:')
    if '状态' in df.columns:
        print(df['状态'].value_counts().to_string())

    print(f'\n项目列表 ({df["项目"].nunique()}个):')
    for p in sorted(df['项目'].unique()):
        cnt = len(df[df['项目'] == p])
        print(f'  {p} ({cnt}条)')

    print(f'\n模块列表 ({df["模块"].nunique()}个):')
    for m in sorted(df['模块'].unique()):
        cnt = len(df[df['模块'] == m])
        print(f'  {m} ({cnt}条)')

    # 任务类型分布
    print(f'\n任务类型分布:')
    if '任务类型' in df.columns:
        print(df['任务类型'].value_counts().to_string())

    # 优先级分布
    print(f'\n优先级分布:')
    if '优先级' in df.columns:
        print(df['优先级'].value_counts().to_string())

    # 3. 对比模板列 vs 数据列
    print('\n' + '=' * 60)
    print('【列名对比】模板 vs 实际数据')
    print('=' * 60)
    t_cols = set(df_t.columns)
    d_cols = set(df.columns)
    missing_in_data = t_cols - d_cols
    extra_in_data = d_cols - t_cols
    if missing_in_data:
        print(f'模板有但数据缺少 ({len(missing_in_data)}个):')
        for c in sorted(missing_in_data):
            print(f'  - {c}')
    else:
        print('✅ 数据包含模板所有列')
    if extra_in_data:
        print(f'数据有但模板缺少 ({len(extra_in_data)}个):')
        for c in sorted(extra_in_data):
            print(f'  + {c}')

    # 4. 必填字段完整度
    REQUIRED_FIELDS = [
        '任务名称','任务类型','选择类型','优先级','状态','负责人','进度',
        '开始日期','结束日期','描述','FS状态','FS负责人','FS计划结束日期',
        '业务测试状态','业务测试负责人','业务测试计划开始日期','业务测试计划结束日期','TS状态'
    ]
    print('\n' + '=' * 60)
    print('【必填字段完整度统计】')
    print('=' * 60)
    for field in REQUIRED_FIELDS:
        if field in df.columns:
            filled = df[field].astype(str).apply(lambda x: x.strip() not in ['', '-', 'nan', 'None']).sum()
            print(f'  {field}: {filled}/{len(df)} ({filled/len(df)*100:.1f}%)')
        else:
            print(f'  {field}: 列不存在')

    # 5. 验收就绪字段状态
    print('\n' + '=' * 60)
    print('【测试报告字段状态】')
    print('=' * 60)
    for tc in ['系统测试报告','集成测试报告','回归测试报告']:
        if tc in df.columns:
            vals = df[tc].astype(str).value_counts()
            print(f'  {tc}: {dict(vals)}')

    print('\n' + '=' * 60)
    print('【FS/业务测试/TS 状态分布】')
    print('=' * 60)
    for c in ['FS状态','业务测试状态','TS状态']:
        if c in df.columns:
            vals = df[c].astype(str).value_counts()
            print(f'  {c}: {dict(vals)}')

    # 6. 批次分布
    print('\n' + '=' * 60)
    print('【批次推断结果（脚本逻辑）】')
    print('=' * 60)
    def extract_batch(proj):
        if pd.isna(proj): return '未标注批次'
        p = str(proj)
        if '-A批次' in p or p.endswith('-A'): return 'A批次'
        if '-B批次' in p or p.endswith('-B'): return 'B批次'
        if '-C批次' in p or '-C' in p: return 'C批次'
        return '未标注批次'
    batches = df['项目'].apply(extract_batch)
    print(batches.value_counts().to_string())

    # 7. 系统类型分布
    print('\n' + '=' * 60)
    print('【系统类型分布（脚本逻辑）】')
    print('=' * 60)
    JAVA_KW = ['智能仓储','合同管理','BPM','报销报账','共享融合','司库融合','MDG-JAVA','BPC前端','电子档案']
    JAVA_MOD_KW = ['智能仓储','合同管理','BPM','报销报账','财务共享系统改造','司库融合','MDG','电子档案','SSF']
    def classify_system(row):
        proj = str(row.get('项目',''))
        mod = str(row.get('模块',''))
        for kw in JAVA_KW:
            if kw in proj: return 'JAVA-专业系统'
        for kw in JAVA_MOD_KW:
            if kw in mod: return 'JAVA-专业系统'
        return 'SAP'
    sys_types = df.apply(classify_system, axis=1)
    print(sys_types.value_counts().to_string())
