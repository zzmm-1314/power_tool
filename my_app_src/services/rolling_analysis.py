"""滚撮分析（市场级，24 点版）

数据源：
  - 日前价格：江苏库（bid_space_service.fetch_day_ahead）优先，
              浙江库（db_store.fetch_price，point_type=unified / price_type=day_ahead）补齐
              两者都是 48 点，按 slot 逐点合并后再折算 24 点小时价
  - 市场滚撮：db_store.fetch_market_rolling（tmp_market_rolling，原生 24 点）

口径：
  - 行 = 24 个整点小时段
  - time 列 = "HH:00-HH+1:00"，与市场滚撮 time_type 对齐
  - 市场合计 = D-2/D-3/D-4 三天按电量加权平均
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from services.bid_space_service import fetch_day_ahead
from services.db_store import fetch_market_rolling, fetch_price
from services.day_ahead_parser import _time_to_slot_index
from utils.logger import get_logger

logger = get_logger("services.rolling_analysis")

# 24 小时时段标签（与市场滚撮 time_type 对齐）
HOURS_24: List[str] = [f"{h:02d}:00-{h + 1:02d}:00" for h in range(24)]

# 日前价格来源标记
SOURCE_JS = "jiangsu"
SOURCE_ZJ = "zhejiang"
SOURCE_MIXED = "mixed"
SOURCE_NONE = "none"


def _slot_index(time_label) -> Optional[int]:
    """时间标签 → 48 点槽位；'00:30'→0，'01:00'→1，…，'24:00'→47"""
    idx = _time_to_slot_index(str(time_label or ""))
    if idx is None or idx < 0 or idx >= 48:
        return None
    return idx


def _to_float(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _js_map_48(date_str: str) -> Dict[int, Optional[float]]:
    """江苏库日前价格 → {slot 0~47: price}"""
    result: Dict[int, Optional[float]] = {}
    try:
        pts = fetch_day_ahead(date_str) or []
    except Exception as e:
        logger.warning(f"[RollingAnalysis] 江苏库日前价格查询失败 {date_str}: {e}")
        return result

    for p in pts:
        idx = _slot_index(p.get("time"))
        if idx is None:
            continue
        result[idx] = _to_float(p.get("value"))
    return result


def _zj_map_48(date_str: str) -> Dict[int, Optional[float]]:
    """浙江库（上传数据）日前价格 → {slot 0~47: price}"""
    result: Dict[int, Optional[float]] = {}
    try:
        rows = fetch_price(date_str, "unified", "day_ahead")
    except Exception as e:
        logger.warning(f"[RollingAnalysis] 浙江库日前价格查询失败 {date_str}: {e}")
        return result

    for r in rows or []:
        idx = _slot_index(r.get("time_label"))
        if idx is None:
            continue
        val = _to_float(r.get("value"))
        # 同一槽位已有有效值时不再覆盖（多单元情况下保留先到的有效值）
        if result.get(idx) is not None:
            continue
        result[idx] = val
    return result


def _build_da_map_48(
    date_str: str,
) -> Tuple[Dict[int, Optional[float]], Dict[int, str]]:
    """逐点合并：江苏库优先，缺测点回退浙江库。返回 (价格表, 来源表)"""
    js_map = _js_map_48(date_str)

    # 江苏库 48 个点位未全部取到有效值时，才需要查浙江库补齐
    js_complete = len(js_map) >= 48 and all(
        js_map.get(i) is not None for i in range(48)
    )
    zj_map = {} if js_complete else _zj_map_48(date_str)

    merged: Dict[int, Optional[float]] = {}
    source: Dict[int, str] = {}
    for idx in range(48):
        js_val = js_map.get(idx)
        if js_val is not None:
            merged[idx] = js_val
            source[idx] = SOURCE_JS
            continue
        zj_val = zj_map.get(idx)
        if zj_val is not None:
            merged[idx] = zj_val
            source[idx] = SOURCE_ZJ
        else:
            merged[idx] = None
            source[idx] = SOURCE_NONE
    return merged, source


def _da_48_to_24(
    da_map_48: Dict[int, Optional[float]],
    da_src_48: Dict[int, str],
) -> Tuple[Dict[int, Optional[float]], Dict[int, str]]:
    """48 点 → 24 点：同小时两个半小时点取均值；缺值时取有效一方"""
    hourly: Dict[int, Optional[float]] = {}
    hourly_src: Dict[int, str] = {}
    for h in range(24):
        idxs = (h * 2, h * 2 + 1)
        valid = [(i, da_map_48.get(i)) for i in idxs if da_map_48.get(i) is not None]
        if not valid:
            hourly[h] = None
            hourly_src[h] = SOURCE_NONE
            continue
        hourly[h] = round(sum(v for _, v in valid) / len(valid), 3)
        hourly_src[h] = (
            SOURCE_JS
            if any(da_src_48.get(i) == SOURCE_JS for i, _ in valid)
            else SOURCE_ZJ
        )
    return hourly, hourly_src


def _merge_source(hourly_src: Dict[int, str]) -> str:
    used = {s for s in hourly_src.values() if s != SOURCE_NONE}
    if not used:
        return SOURCE_NONE
    if used == {SOURCE_JS}:
        return SOURCE_JS
    if used == {SOURCE_ZJ}:
        return SOURCE_ZJ
    return SOURCE_MIXED


def get_rolling_analysis(target_date_str: str) -> dict:
    if not target_date_str:
        raise ValueError("缺少标的日参数")

    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("日期格式错误，应为 YYYY-MM-DD")

    d2_date = (target_date - timedelta(days=2)).strftime("%Y-%m-%d")
    d3_date = (target_date - timedelta(days=3)).strftime("%Y-%m-%d")
    d4_date = (target_date - timedelta(days=4)).strftime("%Y-%m-%d")

    da_map_48, da_src_48 = _build_da_map_48(target_date_str)
    da_hourly, da_src_hourly = _da_48_to_24(da_map_48, da_src_48)

    m2 = fetch_market_rolling(d2_date)
    m3 = fetch_market_rolling(d3_date)
    m4 = fetch_market_rolling(d4_date)

    def _pick(mkt: Dict[int, Dict], hour_idx: int) -> tuple:
        info = mkt.get(hour_idx)
        if not info:
            return 0.0, 0.0
        return float(info["total_qty"]), float(info["avg_price"])

    rows = []
    for h in range(24):
        da_price = da_hourly.get(h)
        d2_qty, d2_price = _pick(m2, h)
        d3_qty, d3_price = _pick(m3, h)
        d4_qty, d4_price = _pick(m4, h)

        d2_diff = (
            round(d2_price - da_price, 3)
            if (d2_price > 0 and da_price is not None)
            else None
        )
        d3_diff = (
            round(d3_price - da_price, 3)
            if (d3_price > 0 and da_price is not None)
            else None
        )
        d4_diff = (
            round(d4_price - da_price, 3)
            if (d4_price > 0 and da_price is not None)
            else None
        )

        total_qty = d2_qty + d3_qty + d4_qty
        if total_qty > 0:
            market_price = (
                d2_qty * d2_price + d3_qty * d3_price + d4_qty * d4_price
            ) / total_qty
            market_diff = (
                round(market_price - da_price, 3) if da_price is not None else None
            )
        else:
            market_price = 0.0
            market_diff = None

        rows.append(
            {
                "time": HOURS_24[h],
                "dayAheadPrice": round(da_price, 3) if da_price is not None else None,
                "dayAheadSource": da_src_hourly.get(h, SOURCE_NONE),
                "d2Qty": round(d2_qty, 3),
                "d2Price": round(d2_price, 3),
                "d2Diff": d2_diff,
                "d3Qty": round(d3_qty, 3),
                "d3Price": round(d3_price, 3),
                "d3Diff": d3_diff,
                "d4Qty": round(d4_qty, 3),
                "d4Price": round(d4_price, 3),
                "d4Diff": d4_diff,
                "marketQty": round(total_qty, 3),
                "marketPrice": round(market_price, 3),
                "marketDiff": market_diff,
            }
        )

    return {
        "targetDate": target_date_str,
        "d2Date": d2_date,
        "d3Date": d3_date,
        "d4Date": d4_date,
        "dayAheadSource": _merge_source(da_src_hourly),
        "dayAheadHours": sum(1 for v in da_hourly.values() if v is not None),
        "marketDates": {
            "d2": bool(m2),
            "d3": bool(m3),
            "d4": bool(m4),
        },
        "rows": rows,
    }