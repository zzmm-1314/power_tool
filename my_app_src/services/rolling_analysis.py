"""滚撮分析（市场级，24 点版）

数据源：
  - 日前价格：bid_space_service.fetch_day_ahead（外部库 48 点）→ 同小时两半点取均值 → 24 点
  - 市场滚撮：db_store.fetch_market_rolling（tmp_market_rolling，原生 24 点）

口径：
  - 行 = 24 个整点小时段
  - time 列 = "HH:00-HH+1:00"，与市场滚撮 time_type 对齐
  - 市场合计 = D-2/D-3/D-4 三天按电量加权平均
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from services.bid_space_service import fetch_day_ahead
from services.db_store import fetch_market_rolling

# 24 小时时段标签（与市场滚撮 time_type 对齐）
HOURS_24: List[str] = [f"{h:02d}:00-{h + 1:02d}:00" for h in range(24)]


def _build_da_map_48(date_str: str) -> Dict[int, Optional[float]]:
    """日前价格 → {slot_idx 0~47: price}；slot 0='00:30', slot 47='24:00'"""
    pts = fetch_day_ahead(date_str) or []
    result: Dict[int, Optional[float]] = {}
    for p in pts:
        t = p.get("time", "")
        try:
            if t == "24:00":
                idx = 47
            else:
                h, m = t.split(":")
                idx = int(h) * 2 + (1 if int(m) >= 30 else 0) - 1
            if 0 <= idx < 48:
                result[idx] = float(p["value"]) if p.get("value") is not None else None
        except (ValueError, AttributeError):
            continue
    return result


def _da_48_to_24(da_map_48: Dict[int, Optional[float]]) -> Dict[int, Optional[float]]:
    """48 点 → 24 点：同小时两个半小时点取均值；缺值时取有效一方"""
    hourly: Dict[int, Optional[float]] = {}
    for h in range(24):
        a = da_map_48.get(h * 2)
        b = da_map_48.get(h * 2 + 1)
        if a is None and b is None:
            hourly[h] = None
        elif a is None:
            hourly[h] = b
        elif b is None:
            hourly[h] = a
        else:
            hourly[h] = round((a + b) / 2, 3)
    return hourly


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

    da_map_48 = _build_da_map_48(target_date_str)
    da_hourly = _da_48_to_24(da_map_48)

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
        "rows": rows,
    }
