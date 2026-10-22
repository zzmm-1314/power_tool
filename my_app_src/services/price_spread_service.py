"""价差分析服务：日前 − 实时（统一结算点 + 电厂节点）—— 48 点精度"""

import os
from typing import Dict, List, Optional

from services.database_provider import fetch_from_database
from services.day_ahead_parser import (
    TARGET_DEVICE_REAL_TIME,
    _norm_time,
    _time_to_slot_index,
    parse_real_time_price_excel,
)
from services.day_ahead_service import (
    SLOT_TIMES,
    DataSource,
    _empty_heatmap,
    _scan_unified_temp_files,
    read_node_excel,
)
from services.temp_manager import TempManager

# ============================================================
#                    实时价格数据（spread/unified）
# ============================================================


def _spread_unified_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "spread", "unified")
    os.makedirs(d, exist_ok=True)
    return d


def _scan_spread_unified_files() -> List[Dict]:
    items: List[Dict] = []
    d = _spread_unified_dir()
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith((".xlsx", ".xls")):
            continue
        fp = os.path.join(d, fn)
        try:
            items.extend(parse_real_time_price_excel(fp))
        except Exception as e:
            print(f"[SpreadService] 解析实时 {fn} 失败: {e}")
    return items


# ============================================================
#               辅助：raw → 48 槽位数组
# ============================================================


def _raw_to_slots(raw: List[Dict]) -> List[Optional[float]]:
    """把 [{time, value}] 转为长度为 48 的槽位数组
    索引 0='00:30'、1='01:00'、...、47='24:00'
    """
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


# ============================================================
#              价差热力图（48 点通用构建）
# ============================================================


def _empty_spread_heatmap() -> Dict:
    return {
        "dates": [],
        "hours": SLOT_TIMES,  # 48 个时间标签
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
    start_date: Optional[str] = None,  # ← 必须存在
) -> Dict:
    day_map = {it["date"]: it for it in day_items}
    rt_map = {it["date"]: it for it in rt_items}

    common_dates = sorted(set(day_map.keys()) & set(rt_map.keys()))

    # 优先 startDate/endDate；都不传时回退到 days
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
        "source": DataSource.EXCEL,
        "minValue": round(min_v, 3),
        "maxValue": round(max_v, 3),
    }


# ============================================================
#                    统一结算点（日前 − 实时）
# ============================================================


def fetch_spread_heatmap(
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,  # ← 必须存在
) -> Dict:
    day_items = _scan_unified_temp_files()
    rt_items = _scan_spread_unified_files()
    return _build_spread_heatmap(
        day_items, rt_items, end_date, days, start_date=start_date
    )


def fetch_spread_single_day(date: str) -> Dict:
    day_items = [it for it in _scan_unified_temp_files() if it["date"] == date]
    rt_items = [it for it in _scan_spread_unified_files() if it["date"] == date]
    if not day_items or not rt_items:
        return {"date": date, "source": DataSource.EMPTY, "hourly": []}

    day_slots = _raw_to_slots(day_items[-1]["raw"])
    rt_slots = _raw_to_slots(rt_items[-1]["raw"])

    hourly = []
    for i, label in enumerate(SLOT_TIMES):
        a = day_slots[i]
        b = rt_slots[i]
        v = None
        if a is not None and b is not None:
            v = round(a - b, 3)
        hourly.append({"hour": label, "value": v})

    return {"date": date, "source": DataSource.EXCEL, "hourly": hourly}


# ============================================================
#                    电厂节点（日前节点 − 实时节点）
# ============================================================


def _read_spread_plant_node(node_name: str) -> List[Dict]:
    """temp/spread/plant/{node}.xlsx"""
    return read_node_excel(node_name, base_subdir="spread/plant")


def fetch_spread_plant_heatmap(
    node_name: str,
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,  # ← 必须存在
) -> Dict:
    if not node_name:
        return _empty_spread_heatmap()

    day_items = read_node_excel(node_name, base_subdir="day-ahead/plant")
    rt_items = _read_spread_plant_node(node_name)
    return _build_spread_heatmap(
        day_items, rt_items, end_date, days, start_date=start_date
    )


def fetch_spread_plant_single_day(node_name: str, date: str) -> Dict:
    day_items = [
        it
        for it in read_node_excel(node_name, base_subdir="day-ahead/plant")
        if it["date"] == date
    ]
    rt_items = [it for it in _read_spread_plant_node(node_name) if it["date"] == date]
    if not day_items or not rt_items:
        return {"date": date, "source": DataSource.EMPTY, "hourly": []}

    day_slots = _raw_to_slots(day_items[-1]["raw"])
    rt_slots = _raw_to_slots(rt_items[-1]["raw"])

    hourly = []
    for i, label in enumerate(SLOT_TIMES):
        a = day_slots[i]
        b = rt_slots[i]
        v = None
        if a is not None and b is not None:
            v = round(a - b, 3)
        hourly.append({"hour": label, "value": v})

    return {"date": date, "source": DataSource.EXCEL, "hourly": hourly}


# ============================================================
#              单日价格明细（日前 / 实时 / 价差）
# ============================================================


def _empty_daily_prices(date: str) -> Dict:
    return {
        "date": date,
        "hours": SLOT_TIMES,  # 48 个时间标签
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
    """
    返回单日的日前价格、实时价格、价差（各 48 点）。
    - node_type="unified"：temp/day-ahead/unified + temp/spread/unified
    - node_type="plant"  ：temp/day-ahead/plant/{node} + temp/spread/plant/{node}
    """
    if not date:
        return _empty_daily_prices(date)

    if node_type == "unified":
        day_items = [it for it in _scan_unified_temp_files() if it["date"] == date]
        rt_items = [it for it in _scan_spread_unified_files() if it["date"] == date]
    else:
        if not node_name:
            return _empty_daily_prices(date)
        day_items = [
            it
            for it in read_node_excel(node_name, base_subdir="day-ahead/plant")
            if it["date"] == date
        ]
        rt_items = [
            it for it in _read_spread_plant_node(node_name) if it["date"] == date
        ]

    if not day_items or not rt_items:
        return _empty_daily_prices(date)

    day_slots = _raw_to_slots(day_items[-1]["raw"])
    rt_slots = _raw_to_slots(rt_items[-1]["raw"])

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
        "source": DataSource.EXCEL,
    }
