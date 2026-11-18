"""PDF 结算单提取服务（纯后端 pdfplumber 提取）

流程：
    PDF 字节 → _extract_tables（pdfplumber + 水印过滤）→ _extract_from_pages（字段解析）

水印过滤由 utils.pdf_common 完成（旋转 / 浅色 / 超大字号 / 跨页重复），
在 pdfplumber 的 page.filter() 层面剔除水印字符后，再调用 extract_tables()。

对外只有一个入口：
    extract_pdf_data(file_bytes: bytes, fields: dict) -> dict
"""

import os
import re
from typing import List

from utils.pdf_common import (
    WATERMARK_FILTER_ENABLED,
    detect_repeat_watermarks,
    extract_page_tables,
    open_pdf_source,
)
from utils.logger import get_logger

logger = get_logger("services.pdf_extract_service")

NUM_PATTERN = re.compile(r"^[+-]?\d+(\.\d+)?$")


# ============================================================
#                     基础工具
# ============================================================


def _norm(s):
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).replace("／", "/")


def _to_number(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("，", "")
    if s in {"", "-", "--", "—", "/", "None"}:
        return None
    if NUM_PATTERN.match(s):
        return float(s)
    return None


def _cell(row, idx):
    if idx is None or idx < 0 or idx >= len(row):
        return None
    return row[idx]


def _parse_month(filename):
    base = os.path.basename(filename)
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", base)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    return os.path.splitext(base)[0]


# ============================================================
#                     表格提取（pdfplumber）
# ============================================================


def _extract_tables(pdf_bytes: bytes) -> List[List[List]]:
    """从 PDF 字节提取前两页表格（带水印过滤）

    返回结构：
        [
            page1_tables,   # List[table]，每张 table 是 string[][]
            page2_tables,
        ]
    """
    pdf = open_pdf_source(pdf_bytes)
    try:
        if not pdf.pages:
            return []

        # 一次扫描得到水印位置集合（跨页统计必须在所有页上做才准）
        repeat_positions = (
            detect_repeat_watermarks(pdf) if WATERMARK_FILTER_ENABLED else set()
        )

        tables = []
        for page in pdf.pages[:2]:
            page_tables = extract_page_tables(
                page,
                filter_watermark=WATERMARK_FILTER_ENABLED,
                repeat_positions=repeat_positions,
            )
            tables.append(page_tables)
        return tables
    finally:
        pdf.close()


# ============================================================
#                     字段解析（核心逻辑）
# ============================================================


def _extract_from_pages(pages_tables: List[List[List]], fields: dict) -> dict:
    """页面表格 → 字段

    参数：
        pages_tables : [page1_tables, page2_tables]
                       pageN_tables 是 List[table]，每张 table 是 string[][]
        fields       : 请求字段开关 {page1_total_qty: bool, ...}

    返回：
        已填字段字典；未命中的字段不出现
    """
    result = {}

    # ========================================================
    #            第一页：合计行（电量 / 电价 / 电费）
    # ========================================================
    if fields.get("page1_total_qty") or fields.get("page1_total_price"):
        page1_tables = pages_tables[0] if len(pages_tables) > 0 else []

        for table in page1_tables:
            # --- 定位表头行 ---
            header_idx = -1
            idx_map = {}
            for ri, row in enumerate(table):
                cells = [_norm(c) for c in row]
                if any("结算电量/容量" in c for c in cells) and any(
                    "结算电价/均价" in c for c in cells
                ):
                    header_idx = ri
                    for label, key in [
                        ("结算电量/容量", "qty"),
                        ("结算电价/均价", "price"),
                        ("结算电费", "fee"),
                    ]:
                        for ci, cell in enumerate(cells):
                            if label in cell:
                                idx_map[key] = ci
                                break
                    break
            if header_idx == -1:
                continue

            # --- 找合计行 ---
            for row in table[header_idx + 1 :]:
                if not row or not any("合计" in _norm(c) for c in row):
                    continue

                # 探测列偏移：合并单元格会导致表头列号与数据列号错位，
                # 从 -2 到 +2 试一遍，用电量 × 电价 ≈ 电费做校验
                for off in (-2, -1, 0, 1, 2):
                    q = _to_number(_cell(row, idx_map["qty"] + off))
                    p = _to_number(_cell(row, idx_map["price"] + off))
                    fee = (
                        _to_number(_cell(row, idx_map.get("fee", -999) + off))
                        if "fee" in idx_map
                        else None
                    )

                    if q is not None and p is not None:
                        if fee is not None:
                            if abs(q * p - fee) <= max(abs(fee) * 2e-3, 5.0):
                                if fields.get("page1_total_qty"):
                                    result["page1_total_qty"] = q
                                if fields.get("page1_total_price"):
                                    result["page1_total_price"] = p
                                break
                        else:
                            if fields.get("page1_total_qty"):
                                result["page1_total_qty"] = q
                            if fields.get("page1_total_price"):
                                result["page1_total_price"] = p
                            break

                if (
                    result.get("page1_total_qty") is not None
                    or result.get("page1_total_price") is not None
                ):
                    break
            if (
                result.get("page1_total_qty") is not None
                or result.get("page1_total_price") is not None
            ):
                break

    # ========================================================
    #            第二页：日前 / 实时行
    # ========================================================
    need_p2 = any(
        fields.get(k)
        for k in [
            "page2_dayahead_qty",
            "page2_dayahead_price",
            "page2_realtime_qty",
            "page2_realtime_price",
        ]
    )
    if need_p2:
        page2_tables = pages_tables[1] if len(pages_tables) > 1 else []

        for table in page2_tables:
            header_idx = -1
            idx_map = {}
            for ri, row in enumerate(table):
                cells = [_norm(c) for c in row]
                if any("结算电量/容量" in c for c in cells) and any(
                    "电价" in c for c in cells
                ):
                    header_idx = ri
                    for label, key in [("结算电量/容量", "qty"), ("电价", "price")]:
                        for ci, cell in enumerate(cells):
                            if label in cell:
                                idx_map[key] = ci
                                break
                    break
            if header_idx == -1:
                continue

            for row in table[header_idx + 1 :]:
                row_str = "".join([_norm(c) for c in row if c])
                is_dayahead = "日前" in row_str
                is_realtime = "实时" in row_str

                if (
                    is_dayahead
                    and (
                        fields.get("page2_dayahead_qty")
                        or fields.get("page2_dayahead_price")
                    )
                ) or (
                    is_realtime
                    and (
                        fields.get("page2_realtime_qty")
                        or fields.get("page2_realtime_price")
                    )
                ):
                    for off in (-1, 0, 1):
                        q = _to_number(_cell(row, idx_map.get("qty", 0) + off))
                        p = _to_number(_cell(row, idx_map.get("price", 0) + off))
                        if q is not None or p is not None:
                            if is_dayahead:
                                if fields.get("page2_dayahead_qty"):
                                    result["page2_dayahead_qty"] = q
                                if fields.get("page2_dayahead_price"):
                                    result["page2_dayahead_price"] = p
                            if is_realtime:
                                if fields.get("page2_realtime_qty"):
                                    result["page2_realtime_qty"] = q
                                if fields.get("page2_realtime_price"):
                                    result["page2_realtime_price"] = p
                            break

                if (
                    not fields.get("page2_dayahead_qty")
                    or result.get("page2_dayahead_qty") is not None
                ) and (
                    not fields.get("page2_realtime_qty")
                    or result.get("page2_realtime_qty") is not None
                ):
                    break

    # ========================================================
    #            第二页：整表提取（可选）
    # ========================================================
    if fields.get("extract_page2"):
        page2_tables = pages_tables[1] if len(pages_tables) > 1 else []
        combined_table = []
        for table in page2_tables:
            if combined_table:
                combined_table.append([])
            for row in table:
                if any(c is not None and str(c).strip() != "" for c in row):
                    combined_table.append(
                        [str(c).strip() if c is not None else "" for c in row]
                    )
        result["page2_data"] = combined_table

    return result


# ============================================================
#                     唯一对外入口
# ============================================================


def extract_pdf_data(file_bytes: bytes, fields: dict) -> dict:
    """PDF 字节 → 字段（唯一入口）

    调用方：api/monthly.py 的 /extract-pdf（multipart 上传）
    """
    pages_tables = _extract_tables(file_bytes)
    return _extract_from_pages(pages_tables, fields)
