"""负荷 / 光伏数据服务：数据库优先 → 临时 Excel 兜底（仅浙江电网）"""

import os
from typing import Dict, List


from services.database_provider import fetch_from_database
from services.load_parser import (
    TARGET_DEVICE,
    detect_kind_from_filename,
    parse_load_excel,
)
from services.temp_manager import TempManager
from utils.dataframe import df_to_points
from datetime import datetime, timedelta


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
    if "excel" in sources:
        return DataSource.EXCEL
    if "database" in sources:
        return DataSource.DB
    return DataSource.EMPTY


class DataSource:
    DB = "database"
    EXCEL = "excel"
    EMPTY = "empty"


# =========================================================
#                    负荷
# =========================================================


def _load_temp_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "load")
    os.makedirs(d, exist_ok=True)
    return d


def _scan_temp_load_files(date: str) -> List[Dict]:
    """扫描 data/temp/load/ 下所有负荷 Excel，只返回该日期、浙江电网的数据"""
    items: List[Dict] = []
    temp_dir = _load_temp_dir()

    for fn in sorted(os.listdir(temp_dir)):
        if not fn.lower().endswith((".xlsx", ".xls")):
            continue
        fp = os.path.join(temp_dir, fn)

        raw_kind = detect_kind_from_filename(fn)
        if raw_kind in ("pv", "pv_forecast"):
            continue  # 光伏文件不进入负荷曲线

        try:
            parsed = parse_load_excel(fp, kind=raw_kind)
        except Exception as e:
            print(f"[LoadService] 解析负荷 {fn} 失败: {e}")
            continue

        for it in parsed:
            if it["date"] != date:
                continue
            it["_file"] = fp
            it["_filename"] = fn
            items.append(it)

    return items


def fetch_load_data(date: str) -> Dict:
    """获取指定日期的负荷数据（固定浙江电网）"""
    # 1) 数据库
    df = fetch_from_database("load", "", date, TARGET_DEVICE)
    if df is not None and not df.empty:
        return {
            "date": date,
            "source": DataSource.DB,
            "series": [
                {
                    "device": TARGET_DEVICE,
                    "kind": "actual",
                    "points": df_to_points(df),
                }
            ],
        }

    # 2) 临时 Excel
    matched = _scan_temp_load_files(date)
    if matched:
        grouped: Dict[str, Dict] = {}
        for it in matched:
            grouped[it["kind"]] = it  # 同 kind 以最新文件为准
        return {
            "date": date,
            "source": DataSource.EXCEL,
            "series": list(grouped.values()),
        }

    # 3) 无数据
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


def _pv_temp_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "pv")
    os.makedirs(d, exist_ok=True)
    return d


def _scan_temp_pv_files(date: str) -> List[Dict]:
    """扫描 pv + load 两个目录中的光伏文件（兼容旧位置）
    kind ∈ {"pv"（实际）, "pv_forecast"（预测）}
    """
    items: List[Dict] = []

    dirs = [
        _pv_temp_dir(),
        os.path.join(TempManager.base_dir(), "load"),  # 兼容历史遗留
    ]

    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith((".xlsx", ".xls")):
                continue

            raw_kind = detect_kind_from_filename(fn)
            if raw_kind not in ("pv", "pv_forecast"):
                continue

            fp = os.path.join(d, fn)
            try:
                parsed = parse_load_excel(fp, kind=raw_kind)
            except Exception as e:
                print(f"[LoadService] 解析光伏 {fn} 失败: {e}")
                continue

            for it in parsed:
                if it["date"] != date:
                    continue
                it["_file"] = fp
                it["_filename"] = fn
                items.append(it)

    print(
        f"[LoadService] pv 扫描结果：date={date}, "
        f"匹配 {len(items)} 条 → "
        f"{[(it['kind'], it['_filename']) for it in items]}"
    )
    return items


def fetch_pv_data(date: str) -> Dict:
    """获取指定日期的光伏出力：实际 + 预测（浙江电网）"""
    # 1) 数据库
    df = fetch_from_database("pv", "", date, TARGET_DEVICE)
    if df is not None and not df.empty:
        return {
            "date": date,
            "source": DataSource.DB,
            "series": [
                {
                    "device": TARGET_DEVICE,
                    "kind": "pv",
                    "points": df_to_points(df),
                }
            ],
        }

    # 2) 临时 Excel：按 kind 去重（同 kind 以最新文件为准）
    matched = _scan_temp_pv_files(date)
    if matched:
        grouped: Dict[str, Dict] = {}
        for it in matched:
            grouped[it["kind"]] = it

        series_list = [
            {
                "device": it["device"] or TARGET_DEVICE,
                "kind": it["kind"],
                "points": it["points"],
            }
            for it in grouped.values()
        ]
        # 实际在前、预测在后
        series_list.sort(key=lambda s: 0 if s["kind"] == "pv" else 1)

        return {
            "date": date,
            "source": DataSource.EXCEL,
            "series": series_list,
        }

    # 3) 无数据
    return {
        "date": date,
        "source": DataSource.EMPTY,
        "series": [],
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
