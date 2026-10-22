"""日前电价解析器：统一结算点（单节点 48→24）+ 电厂节点（多节点 48→24）"""

import os
import re
from typing import List, Dict, Optional

import pandas as pd

TARGET_DEVICE_UNIFIED = "浙江"
TARGET_DEVICE_REAL_TIME = "浙江电力"
_DATE_PATTERN = re.compile(r"(\d{4})[年\-/.]?(\d{1,2})[月\-/.]?(\d{1,2})")


# ---------- 基础工具 ----------
def _slot_to_time(slot: int) -> str:
    """时间槽索引 → 时间标签
    0 → '00:30', 1 → '01:00', 2 → '01:30', ..., 47 → '24:00'
    """
    if slot == 47:
        return "24:00"
    if slot % 2 == 0:
        return f"{slot // 2:02d}:30"
    return f"{(slot + 1) // 2:02d}:00"


ALL_SLOT_TIMES = [_slot_to_time(i) for i in range(48)]


def extract_date_from_text(text) -> Optional[str]:
    if text is None:
        return None
    m = _DATE_PATTERN.search(str(text))
    if not m:
        return None
    y, mo, d = m.groups()
    try:
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    except ValueError:
        return None


def extract_date_from_filename(filename: str) -> Optional[str]:
    if not filename:
        return None
    base = os.path.basename(filename)
    m = re.search(r"(\d{4})(\d{2})(\d{2})", base)
    if m:
        y, mo, d = m.groups()
        try:
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            pass
    return extract_date_from_text(base)


def _norm_time(t) -> str:
    if pd.isna(t):
        return ""
    s = str(t).strip()
    if not s:
        return ""
    if ":" in s:
        parts = s.split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            return f"{h:02d}:{m:02d}"
        except ValueError:
            return s
    return s


def _find_header_row(df: pd.DataFrame, max_scan: int = 15) -> Optional[int]:
    for i in range(min(max_scan, len(df))):
        row_vals = [str(v) for v in df.iloc[i].tolist() if pd.notna(v)]
        if any(("设备名" in v) or ("装置" in v) for v in row_vals):
            return i
    return 2 if len(df) > 2 else None


def _time_to_slot_index(time_str: str) -> Optional[int]:
    """'00:30'→0, '01:00'→1, ..., '24:00'→47"""
    if not time_str or ":" not in time_str:
        return None
    try:
        h, m = time_str.split(":")
        h, m = int(h), int(m)
    except ValueError:
        return None
    if h == 24 and m == 0:
        return 47
    if h > 23 or m not in (0, 30):
        return None
    return h * 2 + (m // 30) - 1


def _slots_to_hourly(slots: List[Optional[float]]) -> List[Optional[float]]:
    """48 槽位 → 24 点（价格保留 3 位小数）"""
    result: List[Optional[float]] = []
    for h in range(24):
        a = slots[h * 2] if h * 2 < len(slots) else None
        b = slots[h * 2 + 1] if h * 2 + 1 < len(slots) else None
        if a is None and b is None:
            result.append(None)
        elif a is None:
            result.append(round(b, 3))
        elif b is None:
            result.append(round(a, 3))
        else:
            result.append(round((a + b) / 2, 3))
    return result


# ---------- 主解析函数（通用） ----------


def parse_price_excel(
    file_path: str,
    device_filter: Optional[str] = None,
) -> List[Dict]:
    """
    解析日前电价 Excel（48 点宽表，多设备行）。
    - device_filter=None  → 返回所有节点（电厂节点）
    - device_filter="浙江" → 只返回该设备（统一结算点）

    返回：[{ date, device, hourly: [{hour, value} × 24], raw: [{time, value} × 48] }]
    """
    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_excel(file_path, header=None, dtype=object)
    except Exception as e:
        print(f"[PriceParser] 读取 {file_path} 失败: {e}")
        return []

    if df.empty or len(df) < 2 or len(df.columns) <= 2:
        return []

    header_row = _find_header_row(df)
    if header_row is None:
        return []

    raw_times = [_norm_time(t) for t in df.iloc[header_row, 2:].tolist()]
    fallback_date = extract_date_from_filename(file_path)

    results: List[Dict] = []
    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]
        if row.isna().all():
            continue

        device = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        if device_filter and device != device_filter:
            continue

        date_text = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        date_str = extract_date_from_text(date_text) or fallback_date
        if not date_str:
            continue

        values = row.iloc[2:].tolist()
        slot_values: List[Optional[float]] = [None] * 48
        raw: List[Dict] = []

        for t, v in zip(raw_times, values):
            idx = _time_to_slot_index(t)
            if idx is None:
                continue
            fv: Optional[float] = None
            if pd.notna(v):
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    fv = None
            slot_values[idx] = fv
            raw.append({"time": t, "value": fv})

        hourly_values = _slots_to_hourly(slot_values)
        hourly_list = [
            {"hour": f"{h + 1:02d}:00", "value": hourly_values[h]} for h in range(24)
        ]

        results.append(
            {
                "date": date_str,
                "device": device,
                "hourly": hourly_list,
                "raw": raw,
            }
        )

    return results


def parse_real_time_price_excel(file_path: str) -> List[Dict]:
    """实时价格：设备名为 '浙江电力'"""
    return parse_price_excel(file_path, device_filter=TARGET_DEVICE_REAL_TIME)


# ---------- 便捷入口 ----------


def parse_unified_price_excel(file_path: str) -> List[Dict]:
    """统一结算点：只返回 '浙江' 设备"""
    return parse_price_excel(file_path, device_filter=TARGET_DEVICE_UNIFIED)


def parse_plant_price_excel(file_path: str) -> List[Dict]:
    """电厂节点：返回文件中所有设备"""
    return parse_price_excel(file_path, device_filter=None)
