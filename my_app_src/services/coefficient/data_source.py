"""从业务数据库构建价差 DataFrame（date + '0'..'47'）"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from services.bid_space_service import fetch_day_ahead_range, fetch_realtime_range
from services.day_ahead_service import load_node_items
from services.price_spread_service import (
    _raw_to_slots,
    load_spread_unified_items,
    load_unified_items,
)
from utils.logger import get_logger

logger = get_logger("services.coefficient.data_source")


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
      - unified：日前统一结算点 + 实时统一结算点
      - plant  ：日前节点 + 实时节点
    返回列：date, '0'..'47'
    """
    if node_type == "plant" and not node_name:
        raise ValueError("节点类型必须提供 node_name")

    # ========================================================
    # 1. 优先尝试从外部业务库（江苏库）一次性拉取并计算
    # ========================================================
    today = datetime.now().strftime("%Y-%m-%d")
    default_start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    query_start = start_date or default_start
    query_end = end_date or today

    query_unit = node_name if node_type == "plant" else None

    # 关键优化：各查 1 次库，一次性拿到整段范围内的数据
    day_data = fetch_day_ahead_range(query_start, query_end, query_unit)
    rt_data = fetch_realtime_range(query_start, query_end, query_unit)

    # 取交集日期
    common_dates = sorted(set(day_data.keys()) & set(rt_data.keys()))
    if start_date:
        common_dates = [d for d in common_dates if d >= start_date]
    if end_date:
        common_dates = [d for d in common_dates if d <= end_date]

    ext_rows = []
    for d in common_dates:
        row = [None] * 48
        day_slots = day_data[d]
        rt_slots = rt_data[d]

        # 在内存中进行 48 点对齐相减
        for i in range(48):
            h = (i + 1) // 2
            mi = 30 if (i % 2 == 0) else 0
            tl = f"{h:02d}:{mi:02d}" if i < 47 else "24:00"

            d_info = day_slots.get(tl)
            r_info = rt_slots.get(tl)

            if d_info and r_info:
                d_val = d_info.get("v2")
                r_val = r_info.get("v2")
                if d_val is not None and r_val is not None:
                    row[i] = d_val - r_val
                else:
                    row[i] = np.nan
            else:
                row[i] = np.nan

        ext_rows.append([pd.Timestamp(d)] + row)

    # 如果外部库获取的数据天数达标（>=30天），则直接组装并返回
    if len(ext_rows) >= 30:
        df = pd.DataFrame(ext_rows, columns=["date"] + [str(i) for i in range(48)])

        # 过滤全 0 / 全空日期
        gap_cols = [str(i) for i in range(48)]
        mask = df[gap_cols].apply(lambda r: np.all(np.abs(r.fillna(0)) < 1e-6), axis=1)
        df = df[~mask].reset_index(drop=True)

        if len(df) >= 30:
            logger.info(
                f"[Coefficient] 成功从外部数据库一次性加载 {len(df)} 天价差数据。"
            )
            return df
        logger.info(
            f"[Coefficient] 外部库有效数据仅 {len(df)} 天，准备降级查询本地数据。"
        )

    # ========================================================
    # 2. 降级：走本地数据库 / 内存预览（原逻辑）
    # ========================================================
    if node_type == "unified":
        day_items = load_unified_items()
        rt_items = load_spread_unified_items()
    else:
        day_items = load_node_items(node_name, base_subdir="day-ahead/plant")
        rt_items = load_node_items(node_name, base_subdir="spread/plant")

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
