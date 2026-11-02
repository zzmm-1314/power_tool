"""日前电价服务：统一结算点 + 电厂节点，数据来自业务数据库

原实现从 data/temp 下的 Excel 文件扫描/读写，该临时存储功能已删除。
现在：上传即解析入库（api/upload.py → services/db_store.replace_points），
本模块只负责从库里读取并组装成热力图 / 单日曲线。
"""

from typing import Dict, List, Optional

from services.database_provider import fetch_series
from services.day_ahead_parser import (
    TARGET_DEVICE_UNIFIED,
    _norm_time,
    _slots_to_hourly,
    _time_to_slot_index,
    parse_plant_price_excel,
)
from services.node_manager import NodeManager


class DataSource:
    DB = "database"
    PREVIEW = "preview"
    EMPTY = "empty"


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


def load_items(data_type: str, sub_type: str, device: Optional[str] = None) -> List[Dict]:
    """读取某类数据（内存预览优先、数据库兜底），组装成 [{date, device, hourly, raw, source}]"""
    records = fetch_series(data_type, sub_type, None, device)
    items: List[Dict] = []
    for rec in records:
        raw = _points_to_raw(rec.get("points"))
        items.append(
            {
                "date": rec["date"],
                "device": rec.get("device") or (device or ""),
                "hourly": _raw_to_hourly(raw),
                "raw": raw,
                "source": rec.get("source") or DataSource.DB,
            }
        )
    return items


def _merge_source(items: List[Dict]) -> str:
    """有预览数据时优先标记为预览，否则按数据库处理"""
    if any(it.get("source") == DataSource.PREVIEW for it in items):
        return DataSource.PREVIEW
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


def load_unified_items() -> List[Dict]:
    """日前 · 统一结算点全部日期数据（供价差分析等复用）"""
    return load_items("day-ahead", "unified", TARGET_DEVICE_UNIFIED)


def fetch_unified_heatmap(
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,
) -> Dict:
    return _build_heatmap_from_items(
        load_unified_items(), end_date, days, start_date=start_date
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


def load_node_items(node_name: str, base_subdir: str = "day-ahead/plant") -> List[Dict]:
    """读取某电厂节点的全部日期数据

    base_subdir 兼容旧调用写法："day-ahead/plant" 或 "spread/plant"
    """
    if not node_name:
        return []
    data_type, sub_type = base_subdir.split("/", 1)
    return load_items(data_type, sub_type, node_name)


# 兼容旧名称
def _read_plant_node_excel(node_name: str) -> List[Dict]:
    return load_node_items(node_name, base_subdir="day-ahead/plant")


# ============================================================
#                  对外查询接口
# ============================================================


def fetch_plant_nodes() -> List[str]:
    """已录入的电厂节点列表"""
    return NodeManager.names()


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
        print(f"[DayAheadService] 解析电厂文件失败: {e}")
        return {}

    grouped: Dict[str, List[Dict]] = {}
    for it in items:
        grouped.setdefault(it["device"], []).append(it)
    return grouped
