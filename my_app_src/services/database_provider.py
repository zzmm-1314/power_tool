"""数据读取层：内存预览优先，业务数据库兜底

数据流：
    上传 Excel → 即时解析 → ① 写入进程内存预览（立即可以显示）
                          → ② 尽力写入 MySQL 业务表 tmp_curve_data（可持久化）

读取时同一维度（类型 + 子类 + 设备/节点 + 日期）以预览为准，其余日期用库里已有数据，
所以刚上传的文件立刻能出图；数据库没配好也不影响预览显示。
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd
from services.constants import DataSource


def _key(rec: Dict) -> tuple:
    return (rec.get("date", ""), rec.get("device", ""), rec.get("kind", ""))


def fetch_record(
    data_type: str,
    sub_type: str,
    date: str,
    device: Optional[str] = None,
) -> Tuple[Optional[List[Dict]], str]:
    """取某一维度的点位，返回 (points, source)；无数据时 (None, "empty")"""
    rows = fetch_series(data_type, sub_type, date, device)
    if not rows:
        return None, "empty"
    rec = rows[-1]
    points = rec.get("points") or []
    if not points:
        return None, "empty"
    return points, rec.get("source", SOURCE_DB)
