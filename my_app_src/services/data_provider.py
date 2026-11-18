"""数据提供者：内存预览优先、业务数据库兜底

原「Excel 临时数据兜底」已随临时存储功能一并移除。
"""

from typing import Optional, Tuple

import pandas as pd
from services.constants import DataSource
from services.database_provider import fetch_record


def fetch_data(
    data_type: str,
    sub_type: str,
    date: str,
    node_name: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    返回 (df, source)
    - df: None 或空表示无数据
    - source: "preview" / "database" / "empty"
    """
    points, source = fetch_record(data_type, sub_type, date, node_name)
    if not points:
        return None, DataSource.EMPTY

    df = pd.DataFrame([{"time": p["time"], "value": p["value"]} for p in points])
    if data_type in ("day-ahead", "spread"):
        df["value"] = pd.to_numeric(df["value"], errors="coerce").round(3)

    return df, source
