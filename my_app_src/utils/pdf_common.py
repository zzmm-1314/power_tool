"""PDF 处理公共能力：水印过滤 + 表格提取

整合原分散在 utils/pdf_parser.py 与 services/pdf_extract_service.py 的 pdfplumber 逻辑，
统一增强水印过滤能力（旋转文字、浅色文字、超大字号、跨页重复文字），供所有 PDF 解析模块复用。

水印算法参考前端 utils/docParser.ts：
  - filterRotate       → 本模块 _is_rotated / _is_light_color / _is_oversized
  - filterHeadersFooters → 本模块 detect_repeat_watermarks

注意：仅能过滤「文字型水印」。图片型水印（logo 图片）需在 page.images 层处理，暂不涉及。
"""

import io
import math
import os
import re
from typing import Dict, List, Optional, Set, Tuple

import pdfplumber
from utils.logger import get_logger

logger = get_logger("utils.pdf_common")

# ============================================================
#                     配置
# ============================================================


def _env_bool(key: str, default: bool = True) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


# 总开关；出现误杀时可通过环境变量关闭
WATERMARK_FILTER_ENABLED = _env_bool("PDF_WATERMARK_FILTER_ENABLED", True)

# 表格识别候选策略（两处原实现完全一致，这里合并）
PDF_TABLE_SETTINGS: List[Dict] = [
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "lines", "horizontal_strategy": "text"},
    {"vertical_strategy": "text", "horizontal_strategy": "text"},
]

# 水印判定阈值
_ROTATION_TOL = 2.0  # 角度容差（度），±tol 内视为水平
_MIN_OVERSIZE = 20.0  # 字号 ≥ 此值视为超大
_LIGHT_THRESHOLD = 0.7  # RGB 各通道 > 此值视为浅色
_REPEAT_RATIO = 0.5  # 跨页重复比例阈值
_MIN_REPEAT = 2  # 至少出现页数


# ============================================================
#                     单字符特征判定
# ============================================================


def _is_rotated(char: dict, tol: float = _ROTATION_TOL) -> bool:
    """字符是否旋转（水印通常 30~45 度斜跨页面）"""
    if char.get("upright", True):
        return False
    m = char.get("matrix")
    if not m or len(m) < 4:
        return True  # 非 upright 且无矩阵信息，保守判旋转
    try:
        angle = math.atan2(m[1], m[0]) * 180 / math.pi
    except (TypeError, ValueError):
        return True
    a = abs(angle)
    return not (a < tol or abs(a - 180) < tol or abs(a - 360) < tol)


def _is_light_color(char: dict, threshold: float = _LIGHT_THRESHOLD) -> bool:
    """颜色是否浅色（水印通常半透明/浅灰）"""
    color = char.get("non_stroking_color")
    if color is None:
        return False
    if not isinstance(color, (list, tuple)):
        return False
    try:
        if len(color) == 3:  # RGB
            r, g, b = (float(c) for c in color)
            return r > threshold and g > threshold and b > threshold
        if len(color) == 1:  # 灰度
            return float(color[0]) > threshold
        if len(color) == 4:  # CMYK，近似转 RGB
            c, m, y, k = (float(x) for x in color)
            return (
                (1 - c) * (1 - k) > threshold
                and (1 - m) * (1 - k) > threshold
                and (1 - y) * (1 - k) > threshold
            )
    except (TypeError, ValueError):
        return False
    return False


def _is_oversized(char: dict, min_size: float = _MIN_OVERSIZE) -> bool:
    """字号异常大"""
    try:
        return float(char.get("size", 0)) >= min_size
    except (TypeError, ValueError):
        return False


# ============================================================
#                     跨页重复水印检测
# ============================================================

_PURE_NUMERIC = re.compile(r"^[\d\.\-+,%/\s]+$")


def detect_repeat_watermarks(pdf) -> Set[Tuple[str, float, float]]:
    """跨页重复出现的非纯数字文字视为水印（对应前端 filterHeadersFooters）。

    返回 {(text, round(x0,1), round(top,1))} 集合。
    排除纯数字，避免误伤表格中的重复数值。
    """
    if not WATERMARK_FILTER_ENABLED or len(pdf.pages) < _MIN_REPEAT:
        return set()

    # {key: set(page_idx)}
    location_pages: Dict[Tuple[str, float, float], Set[int]] = {}

    for page_idx, page in enumerate(pdf.pages):
        seen_in_page: Set[Tuple[str, float, float]] = set()
        for char in page.chars:
            text = (char.get("text") or "").strip()
            if not text or _PURE_NUMERIC.match(text):
                continue
            try:
                key = (
                    text,
                    round(float(char.get("x0", 0)), 1),
                    round(float(char.get("top", 0)), 1),
                )
            except (TypeError, ValueError):
                continue
            if key in seen_in_page:
                continue
            seen_in_page.add(key)
            location_pages.setdefault(key, set()).add(page_idx)

    threshold = max(_MIN_REPEAT, int(len(pdf.pages) * _REPEAT_RATIO))
    return {k for k, pages in location_pages.items() if len(pages) >= threshold}


def is_watermark_char(
    char: dict,
    repeat_positions: Optional[Set[Tuple[str, float, float]]] = None,
) -> bool:
    """综合判定单字符是否为水印"""
    if _is_rotated(char):
        return True
    if _is_light_color(char):
        return True
    if _is_oversized(char):
        return True
    if repeat_positions:
        text = (char.get("text") or "").strip()
        try:
            key = (
                text,
                round(float(char.get("x0", 0)), 1),
                round(float(char.get("top", 0)), 1),
            )
        except (TypeError, ValueError):
            return False
        if key in repeat_positions:
            return True
    return False


# ============================================================
#                     表格提取（统一入口）
# ============================================================


def _filter_page(page, repeat_positions: Optional[Set]) -> "pdfplumber.page.Page":
    """返回过滤掉水印字符后的 Page（保留线条/矩形，表格边框不受影响）"""

    def _keep(obj):
        if obj.get("object_type") == "char":
            return not is_watermark_char(obj, repeat_positions)
        return True

    try:
        return page.filter(_keep)
    except Exception as e:
        logger.warning(f"[PDF] 水印过滤失败，回退原页面: {e}")
        return page


def extract_page_tables(
    page,
    settings_candidates: Optional[List[Dict]] = None,
    filter_watermark: Optional[bool] = None,
    repeat_positions: Optional[Set] = None,
) -> List[List[List[str]]]:
    """从单页提取表格，自动尝试多套 settings 策略（原两处实现合并）。

    返回 pdfplumber 表格结构：[[["单元格", ...], ...], ...]
    """
    if filter_watermark is None:
        filter_watermark = WATERMARK_FILTER_ENABLED

    target = _filter_page(page, repeat_positions) if filter_watermark else page

    for s in settings_candidates or PDF_TABLE_SETTINGS:
        settings = {
            **s,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "intersection_tolerance": 5,
        }
        try:
            tables = target.extract_tables(table_settings=settings) or []
            tables = [t for t in tables if t and any(any(c for c in row) for row in t)]
            if tables:
                return tables
        except Exception as e:
            logger.debug(f"[PDF] 表格策略失败 {s}: {e}")
    return []


# ============================================================
# ============================================================


def open_pdf_source(source) -> "pdfplumber.pdf.PDF":
    """统一打开 PDF，source 支持路径 / bytes / BytesIO"""
    if isinstance(source, (bytes, bytearray)):
        return pdfplumber.open(io.BytesIO(source))
    return pdfplumber.open(source)
