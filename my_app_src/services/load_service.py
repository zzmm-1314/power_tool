"""负荷 / 光伏数据服务：「业务数据库（江苏库优先、浙江库兜底）」（仅浙江电网）

上传入口解析 Excel 后同时写入内存预览与 tmp_curve_data 表，
本模块读取时同一维度以预览为准，因此刚上传即可显示。
"""

from typing import Dict
from datetime import datetime, timedelta
from services.bid_space_service import fetch_load, fetch_pv
from services.db_store import fetch_load_pv, clear_load_pv
from services.load_parser import TARGET_DEVICE
from services.constants import DataSource


def _iterate_date_range(start_date: str, end_date: str, max_days: int = 60):
    """遍历 [start, end]，自动纠正顺序，超过 max_days 截断"""
    try:
        s = datetime.strptime(start_date, "%Y-%m-%d").date()
        e = datetime.strptime(end_date, "%Y-%m-%d").date()
    except Exception:
        return []
    if e < s:
        s, e = e, s
    days = (e - s).days + 1
    if days > max_days:
        e = s + timedelta(days=max_days - 1)
    result = []
    cur = s
    while cur <= e:
        result.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return result


def _merge_source(sources: set) -> str:
    if DataSource.DB in sources:
        return DataSource.DB
    return DataSource.EMPTY


# =========================================================
#                    负荷
# =========================================================


def fetch_load_data(date: str) -> Dict:
    """获取指定日期的负荷数据：优先江苏库，降级浙江库"""
    # 1. 尝试外部库（江苏）
    external_points = fetch_load(date)
    if external_points:
        forecast_pts = [
            {"time": p["time"], "value": p["value"]}
            for p in external_points
            if p.get("value") is not None
        ]
        actual_pts = [
            {"time": p["time"], "value": p["actual"]}
            for p in external_points
            if p.get("actual") is not None
        ]

        series = []
        if forecast_pts:
            series.append(
                {"device": TARGET_DEVICE, "kind": "forecast", "points": forecast_pts}
            )
            clear_load_pv(date, "load", "forecast", TARGET_DEVICE)  # 清理浙江库
        if actual_pts:
            series.append(
                {"device": TARGET_DEVICE, "kind": "actual", "points": actual_pts}
            )
            clear_load_pv(date, "load", "actual", TARGET_DEVICE)  # 清理浙江库

        if series:
            return {"date": date, "source": DataSource.DB, "series": series}

    # 2. 降级：从浙江本地库查
    forecast_rows = fetch_load_pv(date, "load", "forecast", TARGET_DEVICE)
    actual_rows = fetch_load_pv(date, "load", "actual", TARGET_DEVICE)

    series = []
    if forecast_rows:
        series.append(
            {
                "device": TARGET_DEVICE,
                "kind": "forecast",
                "points": [
                    {"time": r["time_label"], "value": r["value"]}
                    for r in forecast_rows
                ],
            }
        )
    if actual_rows:
        series.append(
            {
                "device": TARGET_DEVICE,
                "kind": "actual",
                "points": [
                    {"time": r["time_label"], "value": r["value"]} for r in actual_rows
                ],
            }
        )

    return {
        "date": date,
        "source": DataSource.DB if series else DataSource.EMPTY,
        "series": series,
    }


# =========================================================
#                    负荷 · 范围查询
# =========================================================


def fetch_load_range(start_date: str, end_date: str) -> Dict:
    """负荷范围查询：返回范围内每天的负荷曲线（按日期分组）"""
    dates = _iterate_date_range(start_date, end_date)
    if not dates:
        return {
            "startDate": start_date,
            "endDate": end_date,
            "source": DataSource.EMPTY,
            "series": [],
        }

    series_list = []
    sources = set()
    for d in dates:
        day = fetch_load_data(d)
        sources.add(day["source"])
        for s in day["series"]:
            series_list.append(
                {
                    "date": d,
                    "device": s.get("device", ""),
                    "kind": s["kind"],
                    "points": s["points"],
                }
            )

    return {
        "startDate": start_date,
        "endDate": end_date,
        "source": _merge_source(sources),
        "series": series_list,
    }


# =========================================================
#                    光伏出力
# =========================================================


def fetch_pv_data(date: str) -> Dict:
    """优先从外部业务库读取光伏"""
    # 1. 尝试外部库（江苏）
    external_points = fetch_pv(date)
    if external_points:
        forecast_pts = [
            {"time": p["time"], "value": p["value"]}
            for p in external_points
            if p.get("value") is not None
        ]
        actual_pts = [
            {"time": p["time"], "value": p["actual"]}
            for p in external_points
            if p.get("actual") is not None
        ]

        series = []
        if forecast_pts:
            series.append(
                {"device": TARGET_DEVICE, "kind": "pv_forecast", "points": forecast_pts}
            )
            clear_load_pv(date, "pv", "forecast", TARGET_DEVICE)
        if actual_pts:
            series.append({"device": TARGET_DEVICE, "kind": "pv", "points": actual_pts})
            clear_load_pv(date, "pv", "actual", TARGET_DEVICE)

        if series:
            return {"date": date, "source": DataSource.DB, "series": series}

    # 2. 降级：从浙江本地库查
    forecast_rows = fetch_load_pv(date, "pv", "forecast", TARGET_DEVICE)
    actual_rows = fetch_load_pv(date, "pv", "actual", TARGET_DEVICE)

    series = []
    if forecast_rows:
        series.append(
            {
                "device": TARGET_DEVICE,
                "kind": "pv_forecast",
                "points": [
                    {"time": r["time_label"], "value": r["value"]}
                    for r in forecast_rows
                ],
            }
        )
    if actual_rows:
        series.append(
            {
                "device": TARGET_DEVICE,
                "kind": "pv",
                "points": [
                    {"time": r["time_label"], "value": r["value"]} for r in actual_rows
                ],
            }
        )

    # 保持原有排序：实际在前，预测在后
    series.sort(key=lambda s: 0 if s["kind"] == "pv" else 1)

    return {
        "date": date,
        "source": DataSource.DB if series else DataSource.EMPTY,
        "series": series,
    }


# =========================================================
#                    光伏 · 范围查询
# =========================================================


def fetch_pv_range(start_date: str, end_date: str) -> Dict:
    dates = _iterate_date_range(start_date, end_date)
    if not dates:
        return {
            "startDate": start_date,
            "endDate": end_date,
            "source": DataSource.EMPTY,
            "series": [],
        }

    series_list = []
    sources = set()
    for d in dates:
        day = fetch_pv_data(d)
        sources.add(day["source"])
        for s in day["series"]:
            series_list.append(
                {
                    "date": d,
                    "device": s.get("device", ""),
                    "kind": s["kind"],
                    "points": s["points"],
                }
            )

    return {
        "startDate": start_date,
        "endDate": end_date,
        "source": _merge_source(sources),
        "series": series_list,
    }
