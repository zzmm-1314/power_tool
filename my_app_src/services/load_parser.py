"""负荷 Excel 解析器 —— 兼容「96 点宽表」格式"""

import os
import re
from typing import List, Dict, Optional

import pandas as pd

# ========== 目标设备：只保留该设备的数据 ==========
TARGET_DEVICE = "浙江电网"
# 匹配 2026-10-16 / 2026年10月16日 / 20261016
_DATE_PATTERN = re.compile(r"(\d{4})[年\-/.]?(\d{1,2})[月\-/.]?(\d{1,2})")


def extract_date_from_text(text: str) -> Optional[str]:
    """从任意文本里提取 YYYY-MM-DD"""
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
    """从文件名提取日期：'实际负荷20261016.xlsx' → '2026-10-16'"""
    if not filename:
        return None
    base = os.path.basename(filename)

    # 优先匹配紧凑 8 位数字（20261016）
    m = re.search(r"(\d{4})(\d{2})(\d{2})", base)
    if m:
        y, mo, d = m.groups()
        try:
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        except ValueError:
            pass

    return extract_date_from_text(base)


def _norm_time(t) -> str:
    """标准化时间标签：'00:15' / '0:15' / '0.25' → 'HH:MM'"""
    if pd.isna(t):
        return ""
    s = str(t).strip()
    if not s:
        return ""
    # 已是 HH:MM 格式
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
    """定位表头行（包含 '设备名' / '时间' 关键字的行）"""
    for i in range(min(max_scan, len(df))):
        row_vals = [str(v) for v in df.iloc[i].tolist() if pd.notna(v)]
        if any(("设备名" in v) or ("装置" in v) or ("测点" in v) for v in row_vals):
            return i
    # 回退：默认第 3 行（索引 2）
    return 2 if len(df) > 2 else None


def parse_load_excel(
    file_path: str,
    kind: str = "actual",
    device_filter: Optional[str] = TARGET_DEVICE,
) -> List[Dict]:
    """
    解析负荷 Excel。返回：
    [
        {
            "date": "2026-10-16",
            "device": "浙江电网",
            "kind": "actual",
            "points": [{"time": "00:15", "value": 71785.56}, ...],
        },
        ...
    ]

    device_filter:
        - 默认为 "浙江电网"，只保留该设备的行
        - 传 None 表示不过滤（保留所有设备）
    """
    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_excel(file_path, header=None, dtype=object)
    except Exception as e:
        print(f"[LoadParser] 读取 {file_path} 失败: {e}")
        return []

    if df.empty or len(df) < 2 or len(df.columns) <= 2:
        return []

    header_row = _find_header_row(df)
    if header_row is None:
        return []

    time_labels = [_norm_time(t) for t in df.iloc[header_row, 2:].tolist()]
    if sum(1 for t in time_labels if t) < 20:
        time_labels = [f"{slot // 4:02d}:{(slot % 4) * 15:02d}" for slot in range(96)]

    results: List[Dict] = []
    for i in range(header_row + 1, len(df)):
        row = df.iloc[i]
        if row.isna().all():
            continue

        # --- 设备名（先取，用于过滤）---
        device = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        if device_filter and device != device_filter:
            print(f"[LoadParser] 跳过非目标设备行: {device!r}")
            continue

        # --- 日期 ---
        date_text = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        date_str = extract_date_from_text(date_text)
        if not date_str:
            date_str = extract_date_from_filename(file_path)
        if not date_str:
            continue

        # --- 96 点数值 ---
        values = row.iloc[2:].tolist()
        points = []
        for t, v in zip(time_labels, values):
            if not t or pd.isna(v):
                continue
            try:
                points.append({"time": t, "value": float(v)})
            except (TypeError, ValueError):
                continue

        if not points:
            continue

        results.append(
            {
                "date": date_str,
                "device": device,
                "kind": kind,
                "points": points,
            }
        )

    return results


def detect_kind_from_filename(filename: str) -> str:
    """从文件名判断数据类型
    返回值：
        actual       —— 负荷实际
        forecast     —— 负荷预测
        pv           —— 光伏实际
        pv_forecast  —— 光伏预测
    """
    name = (filename or "").lower()
    is_pv = ("光伏" in name) or ("新能源" in name) or ("pv" in name)
    is_forecast = ("预测" in name) or ("forecast" in name)

    if is_pv:
        return "pv_forecast" if is_forecast else "pv"
    return "forecast" if is_forecast else "actual"
