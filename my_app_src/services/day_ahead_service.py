"""日前电价服务：统一结算点（单节点） + 电厂节点（节点专属 Excel）"""

import os
from typing import Dict, List, Optional

import pandas as pd

from services.database_provider import fetch_from_database
from services.day_ahead_parser import (
    ALL_SLOT_TIMES,
    TARGET_DEVICE_UNIFIED,
    _norm_time,
    _slot_to_time,
    _slots_to_hourly,
    _time_to_slot_index,
    extract_date_from_text,
    parse_plant_price_excel,
    parse_unified_price_excel,
)
from services.temp_manager import TempManager, _safe
from services.node_manager import NodeManager


class DataSource:
    DB = "database"
    EXCEL = "excel"
    EMPTY = "empty"


HOURS = [f"{h:02d}:00" for h in range(1, 25)]  # 01:00 ~ 24:00

# 48 点时间标签：00:30 / 01:00 / 01:30 / 02:00 / ... / 23:30 / 24:00
SLOT_TIMES: List[str] = []
for _h in range(24):
    SLOT_TIMES.append(f"{_h:02d}:30")  # slot 0, 2, 4, ...
    SLOT_TIMES.append(f"{_h + 1:02d}:00")  # slot 1, 3, 5, ...
# ============================================================
#                  通用：items → 热力图结构
# ============================================================


def _build_heatmap_from_items(
    items: List[Dict],
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,  # ← 新增
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
        "source": DataSource.EXCEL,
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


# ============================================================
#                  统一结算点
# ============================================================


def _unified_temp_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "day-ahead", "unified")
    os.makedirs(d, exist_ok=True)
    return d


def _scan_unified_temp_files() -> List[Dict]:
    items: List[Dict] = []
    d = _unified_temp_dir()
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith((".xlsx", ".xls")):
            continue
        fp = os.path.join(d, fn)
        try:
            items.extend(parse_unified_price_excel(fp))
        except Exception as e:
            print(f"[DayAheadService] 解析统一结算点 {fn} 失败: {e}")
    return items


def fetch_unified_heatmap(
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,  # ← 新增
) -> Dict:
    items = _scan_unified_temp_files()
    return _build_heatmap_from_items(items, end_date, days, start_date=start_date)


def fetch_unified_single_day(date: str) -> Dict:
    items = [it for it in _scan_unified_temp_files() if it["date"] == date]
    if not items:
        return {"date": date, "source": DataSource.EMPTY, "hourly": [], "raw": []}
    it = items[-1]
    return {
        "date": date,
        "source": DataSource.EXCEL,
        "hourly": it["hourly"],
        "raw": it["raw"],
    }


# ============================================================
#               电厂节点 · 节点专属 Excel
# ============================================================
def _node_file(node_name: str, base_subdir: str = "day-ahead/plant") -> str:
    """temp/{base_subdir}/{node}.xlsx"""
    return os.path.join(
        TempManager.base_dir(), *base_subdir.split("/"), f"{_safe(node_name)}.xlsx"
    )


def _plant_root_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "day-ahead", "plant")
    os.makedirs(d, exist_ok=True)
    return d


def _plant_node_file(node_name: str) -> str:
    """temp/day-ahead/plant/{安全节点名}.xlsx"""
    return os.path.join(_plant_root_dir(), f"{_safe(node_name)}.xlsx")


def _uploads_temp_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "day-ahead", "_uploads")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------- 写：48 点 × 日期 转置表 ----------------


def write_plant_node_data(
    node_name: str,
    date: str,
    raw_points: List[Dict],
    base_subdir: str = "day-ahead/plant",
) -> bool:
    """把某节点某日期的 48 点数据写入节点专属 Excel
    base_subdir 决定写到 day-ahead/plant 还是 spread/plant
    """
    if not node_name or not date:
        return False

    path = _node_file(node_name, base_subdir)

    tv: Dict[str, Optional[float]] = {}
    for pt in raw_points or []:
        t = _norm_time(pt.get("time"))
        if not t:
            continue
        v = pt.get("value")
        tv[t] = float(v) if v is not None else None

    existing: Dict[str, Dict[str, Optional[float]]] = {}
    if os.path.exists(path):
        try:
            df_old = pd.read_excel(path, index_col=0, dtype=object)
            for col in df_old.columns:
                col_str = str(col).strip()
                col_data: Dict[str, Optional[float]] = {}
                for i in range(len(df_old)):
                    row_time = _norm_time(df_old.index[i])
                    raw_v = df_old.iat[i, df_old.columns.get_loc(col)]
                    if pd.notna(raw_v):
                        try:
                            col_data[row_time] = float(raw_v)
                        except (TypeError, ValueError):
                            col_data[row_time] = None
                    else:
                        col_data[row_time] = None
                existing[col_str] = col_data
        except Exception as e:
            print(f"[DayAheadService] 读取旧节点文件失败 {path}: {e}")
            existing = {}

    existing = {k: v for k, v in existing.items() if extract_date_from_text(k) != date}

    new_col: Dict[str, Optional[float]] = {}
    for t in ALL_SLOT_TIMES:
        new_col[t] = tv.get(t)
    existing[date] = new_col

    df_out = pd.DataFrame(existing, index=ALL_SLOT_TIMES)
    df_out.index.name = "time"

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df_out.to_excel(path)
        return True
    except Exception as e:
        print(f"[DayAheadService] 写入节点文件失败 {path}: {e}")
        return False


def read_node_excel(
    node_name: str,
    base_subdir: str = "day-ahead/plant",
) -> List[Dict]:
    """读取 temp/{base_subdir}/{node}.xlsx 返回 [{date, hourly, raw}, ...]"""
    path = _node_file(node_name, base_subdir)
    if not os.path.exists(path):
        return []

    try:
        df = pd.read_excel(path, index_col=0, dtype=object)
    except Exception as e:
        print(f"[DayAheadService] 读取节点 {node_name} 失败: {e}")
        return []

    if df.empty or len(df.columns) == 0:
        return []

    row_map: List[tuple] = []
    for i in range(len(df)):
        t = _norm_time(df.index[i])
        slot = _time_to_slot_index(t) if t else None
        row_map.append((i, t, slot))

    results: List[Dict] = []
    for col in df.columns:
        date_norm = extract_date_from_text(str(col)) or str(col).strip()

        slot_values: List[Optional[float]] = [None] * 48
        raw: List[Dict] = []

        for i, t, slot in row_map:
            raw_v = df.iat[i, df.columns.get_loc(col)]
            fv: Optional[float] = None
            if pd.notna(raw_v):
                try:
                    fv = float(raw_v)
                except (TypeError, ValueError):
                    fv = None
            if slot is not None:
                slot_values[slot] = fv
            if t:
                raw.append({"time": t, "value": fv})

        hourly_values = _slots_to_hourly(slot_values)
        hourly_list = [
            {"hour": f"{h + 1:02d}:00", "value": hourly_values[h]} for h in range(24)
        ]

        results.append(
            {
                "date": date_norm,
                "device": node_name,
                "hourly": hourly_list,
                "raw": raw,
            }
        )

    return results


# ---------------- 读：从节点专属 Excel 组装 items ----------------


# 兼容旧名称
def _read_plant_node_excel(node_name: str) -> List[Dict]:
    return read_node_excel(node_name, base_subdir="day-ahead/plant")


# ---------------- 对外接口 ----------------


def fetch_plant_nodes() -> List[str]:
    """从节点列表读取（内部会先自动扫描目录同步）"""
    return NodeManager.names()


def fetch_plant_heatmap(
    node_name: str,
    end_date: Optional[str] = None,
    days: int = 14,
    start_date: Optional[str] = None,  # ← 新增
) -> Dict:
    if not node_name:
        return _empty_heatmap()
    items = read_node_excel(node_name, base_subdir="day-ahead/plant")
    return _build_heatmap_from_items(items, end_date, days, start_date=start_date)


def fetch_plant_single_day(node_name: str, date: str) -> Dict:
    items = [it for it in _read_plant_node_excel(node_name) if it["date"] == date]
    if not items:
        return {"date": date, "source": DataSource.EMPTY, "hourly": [], "raw": []}
    it = items[-1]
    return {
        "date": date,
        "source": DataSource.EXCEL,
        "hourly": it["hourly"],
        "raw": it["raw"],
    }


# ---------------- 上传即分发（供 api/temp_data.py 调用） ----------------


def import_plant_price_file(tmp_path: str) -> Dict[str, List[Dict]]:
    """
    解析原始文件，按节点分组。
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
