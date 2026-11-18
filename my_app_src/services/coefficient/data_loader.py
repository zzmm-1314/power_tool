# data_loader.py
import pandas as pd
import numpy as np
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("services.coefficient.data_loader")


def load_history_data(file_path, date_col=None):
    """
    加载历史价差数据（宽格式）
    第一列为日期，其余48列为各时段价差（列名任意，但顺序必须与时间顺序一致）
    返回 DataFrame，包含 'date' 列和 '0'...'47' 列
    """
    df = pd.read_excel(file_path, sheet_name="价差")
    # 1. 识别日期列
    if date_col is None:
        date_col = df.columns[0]  # 默认第一列为日期
    # 确保日期列存在
    if date_col not in df.columns:
        raise ValueError(f"日期列 '{date_col}' 不存在。")

    # 2. 提取日期并转换为 datetime
    dates = pd.to_datetime(df[date_col], errors="coerce")
    if dates.isna().any():
        raise ValueError("日期列包含无法解析的日期。")

    # 3. 提取时段列（除日期列之外的所有列）
    period_cols = [col for col in df.columns if col != date_col]
    if len(period_cols) != 48:
        raise ValueError(
            f"时段列数为 {len(period_cols)}，期望 48 列。请检查「{file_path}」中的列是否完整。"
        )

    # 4. 构建时段数据，并强制重命名为 '0'...'47'
    gap_data = df[period_cols].copy()
    gap_data.columns = [str(i) for i in range(48)]  # 直接重命名

    # 5. 组合结果
    result = pd.DataFrame({"date": dates})
    result = pd.concat([result, gap_data], axis=1)
    return result
