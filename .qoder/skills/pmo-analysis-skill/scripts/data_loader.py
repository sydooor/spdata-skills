"""PMO 项目监控分析 — 数据加载、清洗与分类"""

import pandas as pd
import numpy as np
from config import JAVA_PROJECT_KW, JAVA_MODULE_KW


def pct(a, b):
    """百分比计算，分母为0时返回0"""
    return round(a / b * 100, 1) if b > 0 else 0


def is_filled(val):
    """判断字段值是否有效填写（非空、非占位符）"""
    if pd.isna(val):
        return False
    s = str(val).strip()
    return s != '' and s != '-' and s != 'nan'


def extract_batch(proj):
    """从项目名称提取批次标签"""
    if pd.isna(proj):
        return '未标注批次'
    p = str(proj)
    # BPC独立开发批次 — 不跟随A/B/C批次，独立监控
    if '独立开发批次' in p:
        return 'BPC独立开发批次'
    if '-A批次' in p or p.endswith('-A'):
        return 'A批次'
    if '-B批次' in p or p.endswith('-B'):
        return 'B批次'
    if '-C批次' in p or '-C' in p or 'Ｃ批次' in p:
        return 'C批次'
    return '未标注批次'


def extract_team(proj):
    """从项目名称提取供应商团队"""
    if pd.isna(proj):
        return '未知'
    p = str(proj)
    for kw in ['石化盈科', '昆仑数智', '上海汉得', '青岛海信', '山能数科', '中核核信', '浪潮', '中远海科']:
        if kw in p:
            return kw
    return '内部/其他'


def classify_system(row):
    """根据项目名称和模块判断系统类型（JAVA/SAP）"""
    proj = str(row.get('项目', ''))
    mod = str(row.get('模块', ''))
    for kw in JAVA_PROJECT_KW:
        if kw in proj:
            return 'JAVA-专业系统'
    for kw in JAVA_MODULE_KW:
        if kw in mod:
            return 'JAVA-专业系统'
    return 'SAP'


def should_include_project(proj):
    """判断项目是否应纳入分析：
    - 项目名称含「批次」或含「JAVA」或含「BPC」→ 纳入
    - 项目名称含「运维」→ 排除
    """
    if pd.isna(proj):
        return False
    p = str(proj)
    if '运维' in p:
        return False
    if '批次' in p or 'JAVA' in p or 'BPC' in p:
        return True
    return False


def load_and_clean(filepath):
    """加载Excel数据并进行标准化清洗、分类"""
    df = pd.read_excel(filepath, sheet_name=0)

    # ===== 项目过滤：只保留「含批次/JAVA」且「不含运维」的项目 =====
    before = len(df)
    if '项目' in df.columns:
        df = df[df['项目'].apply(should_include_project)].copy()
        after = len(df)
        excluded_projs = before - after
        if excluded_projs > 0:
            print(f'   项目过滤: {before} → {after} 行（排除 {excluded_projs} 行，不含批次/JAVA 或含运维）')

    # 列名映射
    col_map = {'清单项名称': '任务名称'}
    df.rename(columns=col_map, inplace=True)

    # 状态标准化
    status_map = {'已经完成': '已完成', '未开始': '待处理', '已阻塞': '进行中'}
    df['状态_标准'] = df['状态'].replace(status_map)
    if 'FS状态' in df.columns:
        df['FS状态_标准'] = df['FS状态'].replace({'完成': '已完成'}).replace(status_map)
    if '业务测试状态' in df.columns:
        df['业务测试状态_标准'] = df['业务测试状态'].replace({'已经完成': '已完成', '测试中': '进行中', '': '-'})
    if 'TS状态' in df.columns:
        df['TS状态_标准'] = df['TS状态'].replace(status_map)

    # 进度数值化
    df['进度数值'] = df['进度'].astype(str).str.replace('%', '').apply(
        lambda x: float(x) if x.replace('.', '').isdigit() else 0) / 100

    # 人天数值化
    df['人天数值'] = pd.to_numeric(df['计划开发人天'], errors='coerce').fillna(0)

    # 日期解析
    for dcol in ['开始日期', '结束日期', '业务测试计划结束日期']:
        if dcol in df.columns:
            df[dcol + '_dt'] = pd.to_datetime(df[dcol], format='%Y/%m/%d', errors='coerce')

    # 任务周期（工作日，排除周末）
    if '开始日期_dt' in df.columns and '结束日期_dt' in df.columns:
        mask = df['开始日期_dt'].notna() & df['结束日期_dt'].notna()
        df['任务周期'] = np.nan
        df.loc[mask, '任务周期'] = np.busday_count(
            df.loc[mask, '开始日期_dt'].values.astype('datetime64[D]'),
            df.loc[mask, '结束日期_dt'].values.astype('datetime64[D]')
        )

    # 分类标签
    if '项目' in df.columns:
        df['批次'] = df['项目'].apply(extract_batch)
        df['供应商团队'] = df['项目'].apply(extract_team)
    df['系统类型'] = df.apply(classify_system, axis=1)

    # 完成标记（三态：已取消单独标记，不拖低完成率）
    df['完成标记'] = df['状态_标准'].apply(lambda x: '已取消' if x == '已取消' else ('已完成' if x == '已完成' else '未完成'))

    return df
