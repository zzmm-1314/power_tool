"""统调电厂：Excel 导入 / 解析 / 分页查询 / 地图聚合"""

import os
import threading
from typing import Dict, List, Optional

import pandas as pd

from services.temp_manager import TempManager

_lock = threading.Lock()


# 导入目录
def _import_dir() -> str:
    d = os.path.join(TempManager.base_dir(), "unified-plants")
    os.makedirs(d, exist_ok=True)
    return d


def _excel_path() -> str:
    return os.path.join(_import_dir(), "统调电厂.xlsx")


# ============================================================
#                     Excel 解析
# ============================================================


def _norm_text(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).replace("\n", "").replace("<br>", "").strip()


def _norm_city(name: str) -> str:
    """城市名规范化：'宁波' → '宁波市'，兼容带/不带'市'"""
    name = (name or "").strip()
    if not name:
        return ""
    if name.endswith(("市", "自治州", "地区")):
        return name
    return name + "市"


def parse_unified_plant_excel(path: str) -> List[Dict]:
    """
    解析统调电厂 Excel。
    约定列顺序（表头可有换行/占位，按位置读取）：
        A 调度命名 / B 机组序号 / C 铭牌出力(MW) / D 所在城市
    返回：
      [{"plant": "北仑港电厂", "unit": "1", "capacity": 630.0, "city": "宁波市"}, ...]
    """
    if not path or not os.path.exists(path):
        return []

    try:
        df = pd.read_excel(path, header=None, dtype=object)
    except Exception as e:
        print(f"[UnifiedPlant] 读取失败 {path}: {e}")
        return []

    if df.empty or len(df.columns) < 4 or len(df) < 2:
        return []

    rows: List[Dict] = []
    for i in range(1, len(df)):  # 第 1 行为表头
        row = df.iloc[i]
        if row.isna().all():
            continue

        plant = _norm_text(row.iloc[0])
        unit = _norm_text(row.iloc[1])
        cap_raw = row.iloc[2]
        city = _norm_city(_norm_text(row.iloc[3]))

        if not plant:
            continue

        try:
            capacity = float(cap_raw)
        except (TypeError, ValueError):
            capacity = None

        rows.append(
            {
                "plant": plant,
                "unit": unit,
                "capacity": capacity,
                "city": city,
            }
        )

    return rows


# ============================================================
#                     导入 / 覆盖
# ============================================================


def save_import(file_storage) -> Dict:
    """保存上传的 Excel 到导入目录（同名覆盖）"""
    if file_storage is None or not file_storage.filename:
        return {"ok": False, "error": "未选择文件"}

    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        return {"ok": False, "error": "仅支持 .xlsx / .xls 文件"}

    path = _excel_path()

    with _lock:
        # 先删旧的，再存新的（保持最新）
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

        # 以统一文件名保存
        file_storage.save(path)

        # 立即解析，校验结果
        items = parse_unified_plant_excel(path)

    return {
        "ok": True,
        "path": os.path.relpath(path, TempManager.base_dir()).replace("\\", "/"),
        "count": len(items),
        "cities": len({it["city"] for it in items if it["city"]}),
        "plants": len({it["plant"] for it in items}),
    }


def clear_import() -> Dict:
    path = _excel_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError as e:
            return {"ok": False, "error": f"删除失败: {e}"}
    return {"ok": True}


# ============================================================
#                     查询 / 聚合
# ============================================================


def _load_all() -> List[Dict]:
    path = _excel_path()
    if not os.path.exists(path):
        return []
    return parse_unified_plant_excel(path)


def list_paged(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    city: str = "",
) -> Dict:
    """分页查询（keyword 匹配电厂名 / 城市 / 机组号）"""
    items = _load_all()

    kw = (keyword or "").strip().lower()
    city = (city or "").strip()

    if kw:
        items = [
            it
            for it in items
            if kw in it["plant"].lower()
            or kw in it["city"].lower()
            or kw in it["unit"].lower()
        ]
    if city:
        items = [it for it in items if it["city"] == city]

    total = len(items)
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": items[start:end],
    }


def map_aggregation() -> Dict:
    """按城市聚合：电厂数量 / 机组数量 / 铭牌出力合计"""
    items = _load_all()

    by_city: Dict[str, Dict] = {}
    for it in items:
        c = it["city"] or "未知"
        if c not in by_city:
            by_city[c] = {
                "city": c,
                "plants": set(),
                "unitCount": 0,
                "totalCapacity": 0.0,
            }
        by_city[c]["plants"].add(it["plant"])
        by_city[c]["unitCount"] += 1
        if it["capacity"] is not None:
            by_city[c]["totalCapacity"] += it["capacity"]

    data = []
    for c, agg in by_city.items():
        data.append(
            {
                "city": c,
                "plantCount": len(agg["plants"]),
                "unitCount": agg["unitCount"],
                "totalCapacity": round(agg["totalCapacity"], 2),
            }
        )

    # 按铭牌出力降序，汇总表默认就是有序的
    data.sort(key=lambda x: x["totalCapacity"], reverse=True)

    max_plant = max((d["plantCount"] for d in data), default=0)
    max_capacity = max((d["totalCapacity"] for d in data), default=0)
    total_capacity = sum(d["totalCapacity"] for d in data)

    return {
        "cities": data,
        "maxPlantCount": max_plant,
        "maxCapacity": max_capacity,  # 新增：用于地图 visualMap
        "totalCapacity": round(total_capacity, 2),  # 新增：全省合计
        "totalPlants": len({it["plant"] for it in items}),
        "totalUnits": len(items),
        "totalCities": len(data),
    }


def city_options() -> List[str]:
    return sorted({it["city"] for it in _load_all() if it["city"]})
