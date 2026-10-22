# data_loader.py
import pandas as pd
import numpy as np
from datetime import datetime


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
        # 如果列数不是48，尝试检查是否有 '0'..'47' 命名的列
        # 但为了容错，我们直接取所有其他列，并强制重命名
        print(f"警告：时段列数为 {len(period_cols)}，期望48列。将按顺序重命名。")

    # 4. 构建时段数据，并强制重命名为 '0'...'47'
    gap_data = df[period_cols].copy()
    gap_data.columns = [str(i) for i in range(48)]  # 直接重命名

    # 5. 组合结果
    result = pd.DataFrame({"date": dates})
    result = pd.concat([result, gap_data], axis=1)
    return result


def prepare_weather_data(weather_df, target_date):
    """
    准备天气数据：从包含多日的DataFrame中提取目标日期，并上采样至48点
    weather_df : 包含 'time' (datetime) 和气象字段的DataFrame
    target_date : str or datetime, 预测日期
    返回48行DataFrame
    """
    target = pd.to_datetime(target_date).date()
    day_df = weather_df[weather_df["time"].dt.date == target].copy()
    if len(day_df) != 24:
        raise ValueError(f"目标日期 {target} 数据行数 {len(day_df)}，期望24行")
    day_df = day_df.sort_values("time").reset_index(drop=True)
    # 上采样至48点（简单复制）
    df_48 = pd.DataFrame()
    for col in day_df.columns:
        if col == "time":
            # 生成48个时间点
            times = pd.date_range(start=f"{target} 00:00", periods=48, freq="30min")
            df_48["time"] = times
        else:
            df_48[col] = np.repeat(day_df[col].values, 2)
    return df_48
