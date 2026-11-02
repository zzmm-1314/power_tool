"""负荷 / 光伏数据服务：内存预览优先、业务数据库兜底（仅浙江电网）

上传入口解析 Excel 后同时写入内存预览与 tmp_curve_data 表，
本模块读取时同一维度以预览为准，因此刚上传即可显示。
"""

from typing import Dict
from datetime import datetime, timedelta

from services.database_provider import fetch_series
from services.load_parser import TARGET_DEVICE


class DataSource:
    DB = "database"
    PREVIEW = "preview"
    EMPTY = "empty"


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
    """预览优先：只要有来自内存预览的数据就标记为 preview"""
    if DataSource.PREVIEW in sources:
        return DataSource.PREVIEW
    if DataSource.DB in sources:
        return DataSource.DB
    return DataSource.EMPTY


# =========================================================
#                    负荷
# =========================================================


def fetch_load_data(date: str) -> Dict:
    """获取指定日期的负荷数据（固定浙江电网）"""
    # 同 kind 以最后写入的一条为准（预览覆盖数据库）
    grouped: Dict[str, Dict] = {}
    for rec in fetch_series("load", "", date, TARGET_DEVICE):
        grouped[rec["kind"]] = rec

    if grouped:
        return {
            "date": date,
            "source": _merge_source({r.get("source") for r in grouped.values()}),
            "series": [
                {
                    "device": rec.get("device") or TARGET_DEVICE,
                    "kind": rec["kind"],
                    "points": rec["points"],
                }
                for rec in grouped.values()
            ],
        }

    return {
        "date": date,
        "source": DataSource.EMPTY,
        "series": [],
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
    grouped: Dict[str, Dict] = {}
    for rec in fetch_series("pv", "", date, TARGET_DEVICE):
        grouped[rec["kind"]] = rec

    if not grouped:
        return {
            "date": date,
            "source": DataSource.EMPTY,
            "series": [],
        }

    ordered = sorted(grouped.values(), key=lambda r: 0 if r["kind"] == "pv" else 1)
    return {
        "date": date,
        # ⚠ 修复：原来是 DataSource.DB 写死，导致预览数据被错标为 DB
        "source": _merge_source({r.get("source") for r in grouped.values()}),
        "series": [
            {
                "device": rec.get("device") or TARGET_DEVICE,
                "kind": rec["kind"],
                "points": rec["points"],
            }
            for rec in ordered
        ],
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
