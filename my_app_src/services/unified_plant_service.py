"""统调电厂：Excel 导入 / 解析 / 分页查询 / 地图聚合 (完全基于数据库)"""

import os
import pandas as pd
from typing import Dict, List

from services.db_store import (
    replace_unified_plants,
    fetch_unified_plants,
    fetch_unified_plants_map,
    fetch_unified_plant_cities,
    clear_unified_plants,
)


def _norm_text(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).replace("\n", "").replace("<br>", "").strip()


def _norm_city(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    if name.endswith(("市", "自治州", "地区")):
        return name
    return name + "市"


def parse_unified_plant_excel(file_stream) -> List[Dict]:
    """
    解析统调电厂 Excel (直接接收文件流)
    约定列顺序（表头可有换行/占位，按位置读取）：
        A 调度命名 / B 机组序号 / C 铭牌出力(MW) / D 所在城市
    """
    try:
        df = pd.read_excel(file_stream, header=None, dtype=object)
    except Exception as e:
        print(f"[UnifiedPlant] 读取失败: {e}")
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


def save_import(file_storage) -> Dict:
    """解析上传的 Excel 并覆盖写入数据库"""
    if file_storage is None or not file_storage.filename:
        return {"ok": False, "error": "未选择文件"}

    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        return {"ok": False, "error": "仅支持 .xlsx / .xls 文件"}

    try:
        # 直接读取文件流
        items = parse_unified_plant_excel(file_storage)
        if not items:
            return {"ok": False, "error": "未解析出有效数据，请检查模板"}

        # 批量入库
        replace_unified_plants(items)
    except Exception as e:
        return {"ok": False, "error": f"保存失败: {e}"}

    return {
        "ok": True,
        "count": len(items),
        "cities": len({it["city"] for it in items if it["city"]}),
        "plants": len({it["plant"] for it in items}),
    }


def clear_import() -> Dict:
    try:
        clear_unified_plants()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"清空失败: {e}"}


def list_paged(
    page: int = 1, page_size: int = 20, keyword: str = "", city: str = ""
) -> Dict:
    """分页查询 (从数据库)"""
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))

    res = fetch_unified_plants(page, page_size, keyword, city)

    # ⭐ 强制类型转换
    for item in res["items"]:
        if item.get("capacity") is not None:
            try:
                item["capacity"] = float(item["capacity"])
            except (TypeError, ValueError):
                item["capacity"] = None
        else:
            item["capacity"] = None

    return {
        "total": res["total"],
        "page": page,
        "pageSize": page_size,
        "items": res["items"],
    }


def map_aggregation() -> Dict:
    """按城市聚合地图数据"""
    from services.db_store import fetch_unified_plants_count

    cities_data = fetch_unified_plants_map()

    total_capacity = 0.0
    formatted_cities = []

    for row in cities_data:
        c = row["city"]
        pc = row["plantCount"]
        uc = row["unitCount"]

        # ⭐ 核心修复：将 Decimal 强转为 float
        tc = round(float(row["totalCapacity"] or 0), 2)

        formatted_cities.append(
            {"city": c, "plantCount": pc, "unitCount": uc, "totalCapacity": tc}
        )

        total_capacity += tc

    max_plant = max((d["plantCount"] for d in formatted_cities), default=0)
    max_capacity = max((d["totalCapacity"] for d in formatted_cities), default=0)

    # 从数据库直接查出准确的机组总数
    total_units = fetch_unified_plants_count()

    # 电厂数量从城市聚合列表中简单汇总（同城不同厂，跨城同名电厂极少）
    total_plants = sum(c["plantCount"] for c in formatted_cities)

    return {
        "cities": formatted_cities,
        "maxPlantCount": max_plant,
        "maxCapacity": max_capacity,
        "totalCapacity": round(total_capacity, 2),
        "totalPlants": total_plants,
        "totalUnits": total_units,
        "totalCities": len(formatted_cities),
    }


def city_options() -> List[str]:
    return fetch_unified_plant_cities()


def add_plant(data: dict) -> Dict:
    from services.db_store import add_unified_plant

    try:
        # 补齐城市后缀
        data["city"] = _norm_city(data.get("city", ""))
        new_id = add_unified_plant(data)
        return {"ok": True, "id": new_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def update_plant(record_id: int, data: dict) -> Dict:
    from services.db_store import update_unified_plant

    try:
        data["city"] = _norm_city(data.get("city", ""))
        update_unified_plant(record_id, data)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_plants_batch(ids: List[int]) -> Dict:
    from services.db_store import delete_unified_plants_batch

    try:
        count = delete_unified_plants_batch(ids)
        return {"ok": True, "count": count}
    except Exception as e:
        return {"ok": False, "error": str(e)}
