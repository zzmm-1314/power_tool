"""公用数据库查询接口（占位，等真实数据库接入时替换）"""

from typing import Optional
import pandas as pd


def fetch_from_database(data_type, sub_type, date, node_name=None):
    """
    - load: 负荷（MW），保持原精度
    - day-ahead / spread: 价格（元/MWh），保留 3 位小数
    """
    # 示例：
    #   df = pd.read_sql(...)
    #   if data_type in ("day-ahead", "spread") and "value" in df.columns:
    #       df["value"] = df["value"].round(3)
    #   return df
    return None
