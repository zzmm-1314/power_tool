from typing import List, Dict
import pandas as pd

TIME_KEYS = ("time", "时间", "时刻", "date")
VALUE_KEYS = ("value", "值", "数值", "电量", "电价", "价格")


def df_to_points(df: pd.DataFrame, decimals: int = 0) -> List[Dict]:
    """
    decimals:
        0 → 原样输出（负荷用）
        3 → 价格保留 3 位（day-ahead / spread 用）
    """
    if df is None or df.empty:
        return []

    cols = list(df.columns)
    lower_map = {str(c).lower(): c for c in cols}

    time_col = next((lower_map[k] for k in TIME_KEYS if k in lower_map), cols[0])
    value_col = next((lower_map[k] for k in VALUE_KEYS if k in lower_map), cols[-1])

    points: List[Dict] = []
    for _, row in df.iterrows():
        try:
            v = float(row[value_col])
        except (TypeError, ValueError):
            v = 0.0
        if decimals:
            v = round(v, decimals)
        points.append({"time": str(row[time_col]), "value": v})
    return points
