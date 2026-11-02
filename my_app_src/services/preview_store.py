"""进程内预览缓存：上传解析后的数据先放内存，实现「即时预览、不保存本地」

与 services/db_store.py 接口签名保持一致，便于上层统一调用：
- replace_points()：按 (data_type, sub_type, device, date) 覆盖写入内存
- fetch_items()：按条件读取，返回与 db_store 同构的记录（带 source="preview"）
- clear()：清空预览（可按 data_type 局部清空）
- summary()：当前预览概览，供接口返回提示

数据只存在当前进程内存中，不落盘、不写库，程序重启即消失。
"""

import threading
from typing import Dict, List, Optional

_LOCK = threading.Lock()
# key = (data_type, sub_type, device, date) → 记录字典
_STORE: Dict[tuple, Dict] = {}


def _normalize(points: Optional[List[Dict]]) -> List[Dict]:
    out: List[Dict] = []
    for pt in points or []:
        t = str(pt.get("time") or "").strip()
        if not t:
            continue
        v = pt.get("value")
        try:
            v = float(v) if v is not None else None
        except (TypeError, ValueError):
            v = None
        out.append({"time": t, "value": v})
    return out


def replace_points(
    data_type: str,
    sub_type: str = "",
    device: str = "",
    date: str = "",
    points: Optional[List[Dict]] = None,
    source_file: str = "",
) -> int:
    """把某维度的解析结果写入内存预览（同维度覆盖旧预览）"""
    norm = _normalize(points)
    key = (data_type, sub_type or "", device or "", date)
    with _LOCK:
        _STORE[key] = {
            "date": date,
            "device": device or "",
            "kind": sub_type or "",
            "points": norm,
            "source_file": source_file,
            "source": "preview",
        }
    return len(norm)


def fetch_items(
    data_type: str,
    sub_type: Optional[str] = None,
    date: Optional[str] = None,
    device: Optional[str] = None,
) -> List[Dict]:
    """读取内存预览；sub_type / date / device 为空表示该维度不限"""
    with _LOCK:
        rows = [v for k, v in _STORE.items() if k[0] == data_type]
    out: List[Dict] = []
    for r in rows:
        if sub_type and r["kind"] != sub_type:
            continue
        if date and r["date"] != date:
            continue
        if device and r["device"] != device:
            continue
        out.append(
            {
                "date": r["date"],
                "device": r["device"],
                "kind": r["kind"],
                "points": list(r["points"]),
                "source": "preview",
            }
        )
    return out


def clear(data_type: Optional[str] = None) -> int:
    """清空预览数据；不传 data_type 表示全清。返回清掉的条目数"""
    with _LOCK:
        if not data_type:
            n = len(_STORE)
            _STORE.clear()
            return n
        keys = [k for k in _STORE if k[0] == data_type]
        for k in keys:
            _STORE.pop(k, None)
        return len(keys)


def summary() -> Dict:
    """当前内存预览概览"""
    with _LOCK:
        items = list(_STORE.values())
    return {
        "entries": len(items),
        "totalPoints": sum(len(it["points"]) for it in items),
        "dates": sorted({it["date"] for it in items}),
        "devices": sorted({it["device"] for it in items if it["device"]}),
    }
