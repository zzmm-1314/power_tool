import os
import re
from io import BytesIO
import pdfplumber

SETTINGS_CANDIDATES = [
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "lines", "horizontal_strategy": "text"},
    {"vertical_strategy": "text", "horizontal_strategy": "text"},
]
NUM_PATTERN = re.compile(r"^[+-]?\d+(\.\d+)?$")


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


def _extract_tables(pdf_bytes):
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        if not pdf.pages:
            return []
        tables = []
        # 只处理前两页
        for page in pdf.pages[:2]:
            page_tables = []
            for s in SETTINGS_CANDIDATES:
                settings = {
                    **s,
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                    "intersection_tolerance": 5,
                }
                page_tables = page.extract_tables(table_settings=settings) or []
                page_tables = [
                    t for t in page_tables if t and any(any(c for c in r) for r in t)
                ]
                if page_tables:
                    break
            tables.append(page_tables)
        return tables


def extract_pdf_data(file_bytes: bytes, fields: dict) -> dict:
    pages_tables = _extract_tables(file_bytes)
    result = {}

    # 提取第一页合计行
    if fields.get("page1_total_qty") or fields.get("page1_total_price"):
        page1_tables = pages_tables[0] if len(pages_tables) > 0 else []
        for table in page1_tables:
            # 找表头
            header_idx = -1
            idx_map = {}
            for ri, row in enumerate(table):
                cells = [_norm(c) for c in row]
                if any("结算电量/容量" in c for c in cells) and any(
                    "结算电价/均价" in c for c in cells
                ):
                    header_idx = ri
                    # 找到电量、电价、电费的位置
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

            # 找合计行
            for row in table[header_idx + 1 :]:
                if not row or not any("合计" in _norm(c) for c in row):
                    continue

                # 探测列偏移，从前2列到后2列尝试
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
                            # 核心逻辑：强校验 电量 * 电价 ≈ 电费
                            if abs(q * p - fee) <= max(abs(fee) * 2e-3, 5.0):
                                if fields.get("page1_total_qty"):
                                    result["page1_total_qty"] = q
                                if fields.get("page1_total_price"):
                                    result["page1_total_price"] = p
                                break
                        else:
                            # 如果 PDF 缺失电费列，按顺序兜底
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

    # ======= 第二页：日前 / 实时行解析（常规提取） =======
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
            # 找表头
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

            # 找具体行
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
                    # 尝试偏移量
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
                # 如果已找齐
                if (
                    not fields.get("page2_dayahead_qty")
                    or result.get("page2_dayahead_qty") is not None
                ) and (
                    not fields.get("page2_realtime_qty")
                    or result.get("page2_realtime_qty") is not None
                ):
                    break

    # ======= 提取第二页整表 (可选) =======
    if fields.get("extract_page2"):
        page2_tables = pages_tables[1] if len(pages_tables) > 1 else []
        combined_table = []
        for t_idx, table in enumerate(page2_tables):
            if combined_table:
                combined_table.append([])
            for row in table:
                # 过滤空行
                if any(c is not None and str(c).strip() != "" for c in row):
                    combined_table.append(
                        [str(c).strip() if c is not None else "" for c in row]
                    )
        result["page2_data"] = combined_table

    return result
