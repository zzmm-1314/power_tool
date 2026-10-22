"""数据提供者：数据库优先，Excel 临时数据兜底"""

from typing import Optional, Tuple
import pandas as pd

from services.database_provider import fetch_from_database
from services.temp_manager import TempManager


class DataSource:
    DB = "database"
    EXCEL = "excel"
    EMPTY = "empty"


def fetch_data(
    data_type: str,
    sub_type: str,
    date: str,
    node_name: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], str, Optional[str]]:
    """
    返回 (df, source, temp_path)
    - df: None 或空表示无数据
    - source: "database" / "excel" / "empty"
    - temp_path: 使用 Excel 临时数据时的文件绝对路径
    """
    # ① 数据库
    df = fetch_from_database(data_type, sub_type, date, node_name)
    if df is not None and not df.empty:
        return df, DataSource.DB, None

    # ② Excel 兜底
    df, path = TempManager.load(data_type, sub_type, date, node_name)
    if df is not None and not df.empty:
        return df, DataSource.EXCEL, path

    return None, DataSource.EMPTY, None
