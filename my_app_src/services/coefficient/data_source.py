"""从项目数据目录构建价差 DataFrame（date + '0'..'47'）"""

import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from services.day_ahead_service import read_node_excel
from services.price_spread_service import (
    _raw_to_slots,
    _scan_spread_unified_files,
    _scan_unified_temp_files,
)


def _slots_to_row(slots: List[Optional[float]]) -> List[Optional[float]]:
    return slots


def _items_to_slots_map(items: List[Dict]) -> Dict[str, List[Optional[float]]]:
    result = {}
    for it in items:
        result[it["date"]] = _raw_to_slots(it["raw"])
    return result


def build_gap_df(
    node_type: str = "unified",
    node_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    构建价差 DataFrame：
      - unified：temp/day-ahead/unified + temp/spread/unified
      - plant  ：temp/day-ahead/plant/{node} + temp/spread/plant/{node}
    返回列：date, '0'..'47'
    """
    if node_type == "unified":
        day_items = _scan_unified_temp_files()
        rt_items = _scan_spread_unified_files()
    else:
        if not node_name:
            raise ValueError("节点类型必须提供 node_name")
        day_items = read_node_excel(node_name, base_subdir="day-ahead/plant")
        rt_items = read_node_excel(node_name, base_subdir="spread/plant")

    day_map = _items_to_slots_map(day_items)
    rt_map = _items_to_slots_map(rt_items)

    common_dates = sorted(set(day_map.keys()) & set(rt_map.keys()))
    if start_date:
        common_dates = [d for d in common_dates if d >= start_date]
    if end_date:
        common_dates = [d for d in common_dates if d <= end_date]

    rows = []
    for d in common_dates:
        a = day_map[d]
        b = rt_map[d]
        row = [None] * 48
        for i in range(48):
            if a[i] is None or b[i] is None:
                row[i] = np.nan
            else:
                row[i] = round(a[i] - b[i], 3)
        rows.append([pd.Timestamp(d)] + row)

    if not rows:
        raise ValueError("没有同时存在日前和实时数据的日期")

    df = pd.DataFrame(rows, columns=["date"] + [str(i) for i in range(48)])

    # 过滤全 0 / 全空日期
    gap_cols = [str(i) for i in range(48)]
    mask = df[gap_cols].apply(lambda r: np.all(np.abs(r.fillna(0)) < 1e-6), axis=1)
    df = df[~mask].reset_index(drop=True)

    if len(df) < 30:
        raise ValueError(f"有效价差数据不足（仅 {len(df)} 天），至少需要 30 天")

    return df
