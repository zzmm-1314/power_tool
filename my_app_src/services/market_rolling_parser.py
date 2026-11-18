"""市场滚撮 Excel 解析

模板列（固定顺序，按位置读取）：
    A 标的日开始日期 / B 标的日结束日期 / C 分时段类型
    D 总交易量 / E 最高价 / F 最低价 / G 加权价格 / H 中位数价格
"""

import os
import re
from typing import Dict, List

import pandas as pd
from utils.logger import get_logger

logger = get_logger("services.market_rolling_parser")

_DATE_PATTERN = re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})")


def _extract_date(text) -> str:
    if text is None or pd.isna(text):
        return ""
    m = _DATE_PATTERN.search(str(text))
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


def _time_type_to_seq(t: str) -> int:
    """'00:00-01:00' → 0；'23:00-24:00' → 23"""
    try:
        start = str(t).split("-")[0].strip()
        h = int(start.split(":")[0])
        return max(0, min(23, h))
    except Exception:
        return -1


def _to_float(v) -> float:
    try:
        return float(v) if v is not None and not pd.isna(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def parse_market_rolling_excel(file_path: str) -> List[Dict]:
    """解析市场滚撮 Excel，返回 [{op_date, time_type, ..., seq}, ...]"""
    if not os.path.exists(file_path):
        return []

    try:
        # 优先读「市场交易信息」sheet，没有就取第一个 sheet
        try:
            df = pd.read_excel(file_path, sheet_name="市场交易信息", dtype=object)
        except (ValueError, KeyError):
            df = pd.read_excel(file_path, dtype=object)
    except Exception as e:
        logger.warning(f"[MarketRolling] 读取失败: {e}")
        return []

    if df.empty or len(df.columns) < 8:
        logger.warning(f"[MarketRolling] 列数不足（{len(df.columns)}），跳过")
        return []

    # 按位置取列（A-H）
    col_op = df.columns[0]
    col_end = df.columns[1]
    col_tt = df.columns[2]
    col_qty = df.columns[3]
    col_max = df.columns[4]
    col_min = df.columns[5]
    col_avg = df.columns[6]
    col_med = df.columns[7]

    records: List[Dict] = []
    for _, row in df.iterrows():
        op_date = _extract_date(row[col_op])
        if not op_date:
            continue

        time_type = str(row[col_tt]).strip() if pd.notna(row[col_tt]) else ""
        seq = _time_type_to_seq(time_type)
        if seq < 0:
            continue

        records.append(
            {
                "op_date": op_date,
                "trade_date_start": op_date,
                "trade_date_end": _extract_date(row[col_end]) or op_date,
                "time_type": time_type,
                "total_qty": _to_float(row[col_qty]),
                "max_price": _to_float(row[col_max]),
                "min_price": _to_float(row[col_min]),
                "avg_price": _to_float(row[col_avg]),
                "median_price": _to_float(row[col_med]),
                "seq": seq,
            }
        )

    return records
