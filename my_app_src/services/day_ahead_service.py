"""日前电价服务：统一结算点 + 电厂节点，数据来自业务数据库

原实现从 data/temp 下的 Excel 文件扫描/读写，该临时存储功能已删除。
现在：上传即解析入库（api/upload.py → services/db_store.replace_points），
本模块只负责从库里读取并组装成热力图 / 单日曲线。
"""

from utils.cache import ttl_cache
from typing import Dict, List, Optional
from services.bid_space_service import (
    fetch_day_ahead,
    fetch_dates_in_month,
    _fetch_data,
    fetch_day_ahead_range,
    fetch_realtime_range,
)
from datetime import datetime, timedelta
from services.day_ahead_parser import (
    TARGET_DEVICE_UNIFIED,
    _norm_time,
    _slots_to_hourly,
    _time_to_slot_index,
    parse_plant_price_excel,
)
from utils.logger import get_logger
from services.constants import DataSource
from services.db_store import fetch_price_range, clear_price

logger = get_logger("services.day_ahead_service")
HOURS = [f"{h:02d}:00" for h in range(1, 25)]  # 01:00 ~ 24:00

# 48 点时间标签：00:30 / 01:00 / 01:30 / 02:00 / ... / 23:30 / 24:00
SLOT_TIMES: List[str] = []
for _h in range(24):
    SLOT_TIMES.append(f"{_h:02d}:30")  # slot 0, 2, 4, ...
    SLOT_TIMES.append(f"{_h + 1:02d}:00")  # slot 1, 3, 5, ...


# ============================================================
#          库记录 → 前端所需的 raw / hourly 结构
# ============================================================


def _points_to_raw(points: List[Dict]) -> List[Dict]:
    """库里的点位 → 48 点有序 raw（缺失点补 None，保持时间语义）"""
    slots: List[Optional[float]] = [None] * 48
    for pt in points or []:
        t = _norm_time(pt.get("time"))
        if not t:
            continue
        idx = _time_to_slot_index(t)
        if idx is None:
            continue
        v = pt.get("value")
        slots[idx] = round(float(v), 3) if v is not None else None
    return [{"time": SLOT_TIMES[i], "value": slots[i]} for i in range(48)]


def _raw_to_hourly(raw: List[Dict]) -> List[Dict]:
    """48 点 → 24 点小时均价"""
    slots = [None] * 48
    for i, pt in enumerate(raw):
        idx = _time_to_slot_index(_norm_time(pt.get("time")))
        if idx is not None:
            slots[idx] = pt.get("value")
    hourly_values = _slots_to_hourly(slots)
    return [{"hour": f"{h + 1:02d}:00", "value": hourly_values[h]} for h in range(24)]


def load_items(
    data_type: str,
    sub_type: str,
    device: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict]:
    """日前 / 实时电价读取（range 查询，两次 DB 往返搞定）"""
    from datetime import datetime as _dt, timedelta as _td

    if data_type not in ("day-ahead", "spread"):
        return []
    if sub_type == "plant" and not device:
        return []

    # 默认范围：最近 31 天
    if not start_date or not end_date:
        today = _dt.now().strftime("%Y-%m-%d")
        start_date = (_dt.now() - _td(days=31)).strftime("%Y-%m-%d")
        end_date = today
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    query_unit = device if sub_type == "plant" else None
    price_type = "day_ahead" if data_type == "day-ahead" else "realtime"

    items = []

    # ① 江苏库：一次范围查询
    try:
        if price_type == "day_ahead":
            js_map = fetch_day_ahead_range(start_date, end_date, query_unit)
        else:
            js_map = fetch_realtime_range(start_date, end_date, query_unit)
    except Exception as e:
        logger.warning(f"[LoadItems] 江苏库范围查询失败: {e}")
        js_map = {}

    js_dates: set = set()
    for d in sorted(js_map.keys()):
        slots = js_map[d]
        pts = [
            {"time": t, "value": float(v["v2"]) if v.get("v2") is not None else None}
            for t, v in sorted(slots.items())
            if isinstance(v, dict) and v.get("v2") is not None
        ]
        if not pts:
            continue
        js_dates.add(d)
        # 江苏库命中 → 清理浙江库
        try:
            clear_price(d, sub_type, price_type, query_unit)
        except Exception:
            pass
        items.append(
            {
                "date": d,
                "device": device or "浙江",
                "raw": pts,
                "hourly": _raw_to_hourly(pts),
                "source": "jiangsu",
            }
        )

    # ② 浙江库：一次范围查询，跳过已被江苏库覆盖的日期
    zj_rows = fetch_price_range(start_date, end_date, sub_type, price_type, query_unit)
    zj_grouped: Dict[str, List[Dict]] = {}
    for r in zj_rows:
        d = r["date"]
        if d in js_dates:
            continue

        # ⭐ 核心修复：确保 value 是纯数字
        raw_val = r["value"]
        if raw_val is None or raw_val == "":
            val = None
        else:
            try:
                val = float(raw_val)
            except (TypeError, ValueError):
                val = None

        zj_grouped.setdefault(d, []).append({"time": r["time_label"], "value": val})

    for d in sorted(zj_grouped.keys()):
        pts = zj_grouped[d]
        items.append(
            {
                "date": d,
                "device": device or "浙江",
                "raw": pts,
                "hourly": _raw_to_hourly(pts),
                "source": "zhejiang",
            }
        )

    return items


def _merge_source(items: List[Dict]) -> str:
    return DataSource.DB if items else DataSource.EMPTY


# ============================================================
#                  通用：items → 热力图结构
# ============================================================


def _build_heatmap_from_items(
    items: List[Dict],
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    if not items:
        return _empty_heatmap()

    date_map: Dict[str, Dict] = {}
    for it in items:
        date_map[it["date"]] = it

    all_dates = sorted(date_map.keys())

    # 优先 startDate/endDate；都不传时回退到 days
    if start_date or end_date:
        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]
    else:
        all_dates = all_dates[-max(days, 1) :]

    if not all_dates:
        return _empty_heatmap()

    matrix: List[List[Optional[float]]] = []
    for h_idx in range(24):
        row: List[Optional[float]] = []
        for d in all_dates:
            it = date_map[d]
            v = it["hourly"][h_idx]["value"] if h_idx < len(it["hourly"]) else None
            row.append(v)
        matrix.append(row)

    flat = [v for r in matrix for v in r if v is not None]
    min_v = min(flat) if flat else 0
    max_v = max(flat) if flat else 0

    return {
        "dates": all_dates,
        "hours": HOURS,
        "matrix": matrix,
        "source": _merge_source([date_map[d] for d in all_dates]),
        "minValue": round(min_v, 3),
        "maxValue": round(max_v, 3),
    }


def _empty_heatmap() -> Dict:
    return {
        "dates": [],
        "hours": HOURS,
        "matrix": [],
        "source": DataSource.EMPTY,
        "minValue": 0,
        "maxValue": 0,
    }


def _empty_day(date: str) -> Dict:
    return {"date": date, "source": DataSource.EMPTY, "hourly": [], "raw": []}


# ============================================================
#                  统一结算点
# ============================================================


def load_unified_items(start_date=None, end_date=None) -> List[Dict]:
    """日前 · 统一结算点全部日期数据"""
    return load_items(
        "day-ahead", "unified", TARGET_DEVICE_UNIFIED, start_date, end_date
    )


@ttl_cache(seconds=300)
def fetch_unified_heatmap(
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    return _build_heatmap_from_items(
        load_unified_items(start_date, end_date), end_date, days, start_date=start_date
    )


def fetch_unified_single_day(date: str) -> Dict:
    items = [it for it in load_unified_items() if it["date"] == date]
    if not items:
        return _empty_day(date)
    it = items[-1]
    return {
        "date": date,
        "source": it.get("source") or DataSource.DB,
        "hourly": it["hourly"],
        "raw": it["raw"],
    }


# ============================================================
#               电厂节点（数据在库，不再依赖节点 Excel）
# ============================================================


def load_node_items(
    node_name: str, base_subdir: str = "day-ahead/plant", start_date=None, end_date=None
) -> List[Dict]:
    if not node_name:
        return []
    data_type, sub_type = base_subdir.split("/", 1)
    return load_items(
        data_type, sub_type, node_name, start_date=start_date, end_date=end_date
    )


# 兼容旧名称
def _read_plant_node_excel(node_name: str) -> List[Dict]:
    return load_node_items(node_name, base_subdir="day-ahead/plant")


# ============================================================
#                  对外查询接口
# ============================================================


def fetch_plant_nodes() -> List[str]:
    from services.bid_space_service import fetch_unit_names

    return fetch_unit_names()


def fetch_plant_heatmap(
    node_name: str,
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    if not node_name:
        return _empty_heatmap()
    items = load_node_items(node_name, base_subdir="day-ahead/plant")
    return _build_heatmap_from_items(items, end_date, days, start_date=start_date)


def fetch_plant_single_day(node_name: str, date: str) -> Dict:
    items = [it for it in _read_plant_node_excel(node_name) if it["date"] == date]
    if not items:
        return _empty_day(date)
    it = items[-1]
    return {
        "date": date,
        "source": it.get("source") or DataSource.DB,
        "hourly": it["hourly"],
        "raw": it["raw"],
    }


# ============================================================
#          上传即解析入库（供 api/upload.py 调用）
# ============================================================


def parse_plant_price_file(tmp_path: str) -> Dict[str, List[Dict]]:
    """解析原始文件，按节点分组。
    返回：{ "万华热电": [{"date": ..., "raw": [...]}, ...], ... }
    """
    try:
        items = parse_plant_price_excel(tmp_path)
    except Exception as e:
        logger.warning(f"[DayAheadService] 解析电厂文件失败: {e}")
        return {}

    grouped: Dict[str, List[Dict]] = {}
    for it in items:
        grouped.setdefault(it["device"], []).append(it)
    return grouped
