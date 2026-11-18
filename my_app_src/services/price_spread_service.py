"""价差分析服务：日前 − 实时（统一结算点 + 电厂节点）—— 48 点精度"""

from typing import Dict, List, Optional
from services.day_ahead_parser import (
    TARGET_DEVICE_REAL_TIME,
    _norm_time,
    _time_to_slot_index,
)
from services.day_ahead_service import (
    SLOT_TIMES,
    DataSource,
    _merge_source,
    load_items,
    load_unified_items,
    load_node_items,
)


def load_spread_unified_items(start_date=None, end_date=None) -> List[Dict]:
    """实时 · 统一结算点全部日期数据"""
    return load_items(
        "spread", "unified", TARGET_DEVICE_REAL_TIME, start_date, end_date
    )


def _raw_to_slots(raw: List[Dict]) -> List[Optional[float]]:
    slots: List[Optional[float]] = [None] * 48
    for pt in raw or []:
        t = _norm_time(pt.get("time"))
        if not t:
            continue
        idx = _time_to_slot_index(t)
        if idx is None:
            continue
        v = pt.get("value")
        slots[idx] = float(v) if v is not None else None
    return slots


def _empty_spread_heatmap() -> Dict:
    return {
        "dates": [],
        "hours": SLOT_TIMES,
        "matrix": [],
        "source": DataSource.EMPTY,
        "minValue": 0,
        "maxValue": 0,
    }


def _build_spread_heatmap(
    day_items: List[Dict],
    rt_items: List[Dict],
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    # 数据已经在 load_items 里自动合并了（江苏库优先，浙江库兜底）
    day_map = {it["date"]: it for it in day_items}
    rt_map = {it["date"]: it for it in rt_items}

    common_dates = sorted(set(day_map.keys()) & set(rt_map.keys()))

    if start_date or end_date:
        if start_date:
            common_dates = [d for d in common_dates if d >= start_date]
        if end_date:
            common_dates = [d for d in common_dates if d <= end_date]
    else:
        common_dates = common_dates[-max(days, 1) :]

    if not common_dates:
        return _empty_spread_heatmap()

    day_slots_map = {d: _raw_to_slots(day_map[d]["raw"]) for d in common_dates}
    rt_slots_map = {d: _raw_to_slots(rt_map[d]["raw"]) for d in common_dates}

    matrix: List[List[Optional[float]]] = []
    for slot_idx in range(48):
        row: List[Optional[float]] = []
        for d in common_dates:
            a = day_slots_map[d][slot_idx]
            b = rt_slots_map[d][slot_idx]
            if a is None or b is None:
                row.append(None)
            else:
                row.append(round(a - b, 3))
        matrix.append(row)

    flat = [v for r in matrix for v in r if v is not None]
    min_v = min(flat) if flat else 0
    max_v = max(flat) if flat else 0

    return {
        "dates": common_dates,
        "hours": SLOT_TIMES,
        "matrix": matrix,
        "source": _merge_source(day_items + rt_items),
        "minValue": round(min_v, 3),
        "maxValue": round(max_v, 3),
    }


def _spread_single(day_items: List[Dict], rt_items: List[Dict], date: str) -> Dict:
    if not day_items or not rt_items:
        return {"date": date, "source": DataSource.EMPTY, "hourly": []}

    day_slots = _raw_to_slots(day_items[0]["raw"])
    rt_slots = _raw_to_slots(rt_items[0]["raw"])

    hourly = []
    for i, label in enumerate(SLOT_TIMES):
        a = day_slots[i]
        b = rt_slots[i]
        v = None
        if a is not None and b is not None:
            v = round(a - b, 3)
        hourly.append({"hour": label, "value": v})

    return {
        "date": date,
        "source": _merge_source(day_items + rt_items),
        "hourly": hourly,
    }


# ============================================================
#                    对外查询接口
# ============================================================


def fetch_spread_heatmap(
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    day_items = load_unified_items(start_date, end_date)
    rt_items = load_spread_unified_items(start_date, end_date)
    return _build_spread_heatmap(day_items, rt_items, end_date, days, start_date)


def fetch_spread_single_day(date: str) -> Dict:
    day_items = load_unified_items(date, date)
    rt_items = load_spread_unified_items(date, date)
    return _spread_single(day_items, rt_items, date)


def fetch_spread_plant_heatmap(
    node_name: str,
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    if not node_name:
        return _empty_spread_heatmap()

    day_items = load_node_items(
        node_name,
        base_subdir="day-ahead/plant",
        start_date=start_date,
        end_date=end_date,
    )
    rt_items = load_node_items(
        node_name, base_subdir="spread/plant", start_date=start_date, end_date=end_date
    )
    return _build_spread_heatmap(day_items, rt_items, end_date, days, start_date)


def fetch_spread_plant_single_day(node_name: str, date: str) -> Dict:
    day_items = load_node_items(
        node_name, base_subdir="day-ahead/plant", start_date=date, end_date=date
    )
    rt_items = load_node_items(
        node_name, base_subdir="spread/plant", start_date=date, end_date=date
    )
    return _spread_single(day_items, rt_items, date)


def _empty_daily_prices(date: str) -> Dict:
    return {
        "date": date,
        "hours": SLOT_TIMES,
        "dayAhead": [],
        "realTime": [],
        "spread": [],
        "source": DataSource.EMPTY,
    }


def fetch_spread_daily_prices(
    date: str,
    node_type: str = "unified",
    node_name: Optional[str] = None,
) -> Dict:
    if not date:
        return _empty_daily_prices(date)

    if node_type == "unified":
        day_items = load_unified_items(date, date)
        rt_items = load_spread_unified_items(date, date)
    else:
        if not node_name:
            return _empty_daily_prices(date)
        day_items = load_node_items(
            node_name, base_subdir="day-ahead/plant", start_date=date, end_date=date
        )
        rt_items = load_node_items(
            node_name, base_subdir="spread/plant", start_date=date, end_date=date
        )

    if not day_items or not rt_items:
        return _empty_daily_prices(date)

    day_slots = _raw_to_slots(day_items[0]["raw"])
    rt_slots = _raw_to_slots(rt_items[0]["raw"])

    spread_slots: List[Optional[float]] = []
    for i in range(48):
        a = day_slots[i] if i < len(day_slots) else None
        b = rt_slots[i] if i < len(rt_slots) else None
        if a is None or b is None:
            spread_slots.append(None)
        else:
            spread_slots.append(round(a - b, 3))

    return {
        "date": date,
        "hours": SLOT_TIMES,
        "dayAhead": day_slots,
        "realTime": rt_slots,
        "spread": spread_slots,
        "source": _merge_source(day_items + rt_items),
    }
