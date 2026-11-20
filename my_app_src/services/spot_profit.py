"""滚撮收益模拟计算（省内 / 长三角省间）

滚撮分析页面与模拟结算单共用同一套口径：
  - 日前价格：fetch_day_ahead（48 点）→ 同小时两个半点取均值 → 24 点小时价
  - 省内滚撮（tmp_rolling_spot）：卖方 qty×(price-clear)；买方 -qty×(clear-price)
  - 省间滚撮（tmp_cross_province_spot）：qty×(price-clear)，按买卖方向取符号

电量口径：买入为负、卖出为正。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from services.bid_space_service import fetch_day_ahead
from services.db_store import fetch_rolling_spot, fetch_cross_province_spot

# 省间滚撮按标的日 D-3 成交，按标的日取数时查询窗口需要前移
_QUERY_LOOKBACK_DAYS = 10


class RollingProfitError(ValueError):
    """滚撮收益模拟所需数据缺失（如缺少日前价格）"""


def _hour_label(h: int) -> str:
    return f"{h:02d}:00-{h + 1:02d}:00"


def _is_sell(direction) -> bool:
    d = str(direction or "").strip()
    return ("卖" in d) or ("售" in d)


def _is_buy(direction) -> bool:
    d = str(direction or "").strip()
    return ("买" in d) or ("购" in d)


def build_day_ahead_hour_map(trade_date: str) -> Dict[str, float]:
    """标的日日前出清价 → {'HH:00-HH+1:00': price}；无数据返回 {}"""
    day_pts = fetch_day_ahead(trade_date)
    if not day_pts:
        return {}

    day_dict = {p["time"]: p["value"] for p in day_pts if p.get("value") is not None}
    hour_map: Dict[str, float] = {}
    for h in range(24):
        t1 = f"{h:02d}:30"
        t2 = f"{(h + 1):02d}:00" if h < 23 else "24:00"
        v1 = day_dict.get(t1)
        v2 = day_dict.get(t2)
        if v1 is not None and v2 is not None:
            hour_map[_hour_label(h)] = round((v1 + v2) / 2, 3)
        elif v1 is not None:
            hour_map[_hour_label(h)] = v1
        elif v2 is not None:
            hour_map[_hour_label(h)] = v2
    return hour_map


def _load_records(
    kind: str,
    unit_name: str,
    start_date: str,
    end_date: str,
    by_trade_date: bool,
) -> List[Dict]:
    """读取滚撮记录；by_trade_date=True 时按标的日过滤（查询窗口自动前移）"""
    query_start = start_date
    if by_trade_date:
        query_start = (
            datetime.strptime(start_date, "%Y-%m-%d")
            - timedelta(days=_QUERY_LOOKBACK_DAYS)
        ).strftime("%Y-%m-%d")

    fetch = fetch_rolling_spot if kind == "rolling" else fetch_cross_province_spot
    records = list(fetch(unit_name, query_start, end_date) or [])
    if not by_trade_date:
        return records

    d_start, d_end = start_date[:10], end_date[:10]
    return [r for r in records if d_start <= str(r["trade_date"])[:10] <= d_end]


def _group_by_trade_date(records: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {}
    for r in records:
        grouped.setdefault(str(r["trade_date"])[:10], []).append(r)
    return dict(sorted(grouped.items()))


def _require_day_ahead(t_date: str, items: List[Dict], hour_map: Dict[str, float]):
    """省内/省间滚撮都必须有日前价格，缺失时抛异常"""
    if not hour_map:
        raise RollingProfitError(
            f"标的日 {t_date} 缺少日前出清价格，无法计算滚撮收益，请先补充日前价格数据"
        )
    missing = sorted(
        {str(r["time_type"]) for r in items if str(r["time_type"]) not in hour_map}
    )
    if missing:
        raise RollingProfitError(
            f"标的日 {t_date} 以下时段缺少日前出清价格，无法计算滚撮收益："
            + "、".join(missing)
        )


def _analyze(
    kind: str,
    unit_name: str,
    start_date: str,
    end_date: str,
    by_trade_date: bool,
    require_day_ahead: bool,
) -> Tuple[List[Dict], Dict[str, Dict[str, float]]]:
    """逐条计算滚撮收益，返回（明细 rows，按标的日汇总 daily）"""
    records = _load_records(kind, unit_name, start_date, end_date, by_trade_date)
    detail: List[Dict] = []
    daily: Dict[str, Dict[str, float]] = {}

    for t_date, items in _group_by_trade_date(records).items():
        hour_map = build_day_ahead_hour_map(t_date)
        if require_day_ahead:
            _require_day_ahead(t_date, items, hour_map)

        for r in items:
            t_type = str(r["time_type"])
            clear_price = hour_map.get(t_type, 0.0)
            qty = float(r["qty"])
            price = float(r["price"])

            if kind == "rolling":
                # 省内：卖方按卖出价高于出清价盈利；买方按买入价低于出清价盈利
                trade_qty = qty if _is_sell(r["direction"]) else -qty
                price_diff = (
                    price - clear_price if trade_qty > 0 else clear_price - price
                )
            else:
                # 省间：成交价与出清价之差，买入取负号
                trade_qty = -qty if _is_buy(r["direction"]) else qty
                price_diff = price - clear_price

            fee = trade_qty * price_diff

            row = {
                "opDate": r["op_date"],
                "tradeDate": r["trade_date"],
                "timeType": t_type,
                "direction": r["direction"],
                "qty": qty,
                "price": price,
                "tradeQty": trade_qty,
                "clearPrice": clear_price,
                "priceDiff": round(price_diff, 3),
                "finalDiff": round(fee, 2),
            }
            if kind != "rolling":
                row["tradePath"] = r.get("trade_path", "")
            detail.append(row)

            agg = daily.setdefault(t_date, {"qty": 0.0, "fee": 0.0, "count": 0})
            agg["qty"] += trade_qty
            agg["fee"] += fee
            agg["count"] += 1

    detail.sort(key=lambda x: (x["opDate"], x["tradeDate"], x["timeType"]))
    return detail, daily


def compute_rolling_spot_profit(
    unit_name: str,
    start_date: str,
    end_date: str,
    by_trade_date: bool = False,
    require_day_ahead: bool = False,
) -> List[Dict]:
    """省内滚撮收益明细（滚撮分析页面口径）"""
    detail, _ = _analyze(
        "rolling", unit_name, start_date, end_date, by_trade_date, require_day_ahead
    )
    return detail


def compute_cross_province_profit(
    unit_name: str,
    start_date: str,
    end_date: str,
    by_trade_date: bool = False,
    require_day_ahead: bool = False,
) -> List[Dict]:
    """长三角省间滚撮收益明细（省间分析页面口径）"""
    detail, _ = _analyze(
        "cross", unit_name, start_date, end_date, by_trade_date, require_day_ahead
    )
    return detail


def daily_rolling_spot_summary(
    unit_name: str, start_date: str, end_date: str
) -> Dict[str, Dict[str, float]]:
    """按标的日汇总省内滚撮：{'YYYY-MM-DD': {'qty': 净电量, 'fee': 收益, 'count': 笔数}}"""
    _, daily = _analyze(
        "rolling", unit_name, start_date, end_date, True, True
    )
    return daily


def daily_cross_province_summary(
    unit_name: str, start_date: str, end_date: str
) -> Dict[str, Dict[str, float]]:
    """按标的日汇总省间滚撮：{'YYYY-MM-DD': {'qty': 净电量, 'fee': 收益, 'count': 笔数}}"""
    _, daily = _analyze("cross", unit_name, start_date, end_date, True, True)
    return daily