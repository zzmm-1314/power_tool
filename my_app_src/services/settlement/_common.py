"""settlement builder 公共工具：

- 时间槽 48 点标签 ↔ 索引换算
- 数据库价格 slots dict → 48 点 list
- 分解引擎 + 合约 + 价格数据的公共加载
- 从 c_rows 按 data_type 聚合 48 点

供 general_builder / jiaojiang_builder 复用，消除重复代码。
"""

from datetime import datetime
from typing import Dict, List, Optional
from services.bid_space_service import fetch_day_ahead_range, fetch_realtime_range
from services.db_store import fetch_price_range, clear_price
from utils.logger import get_logger

logger = get_logger("services.settlement.builder")
# ============================================================
#                    时间槽换算
# ============================================================


def time_label_to_idx(t: str) -> int:
    """时间标签 → 48 槽索引。

    '00:30' → 0, '01:00' → 1, ..., '23:30' → 46, '24:00' → 47；
    非标准格式（如 '00:00'）返回 -1。
    """
    t = str(t).strip()
    if t == "24:00":
        return 47
    try:
        h_str, m_str = t.split(":")
        h, m = int(h_str), int(m_str)
    except (ValueError, AttributeError):
        return -1
    if h == 0 and m == 0:
        return -1
    return h * 2 + (1 if m >= 30 else 0) - 1


def idx_to_time_label(i: int) -> str:
    """48 槽索引 → 时间标签。"""
    if i == 47:
        return "24:00"
    h = (i + 1) // 2
    mi = 30 if (i % 2 == 0) else 0
    return f"{h:02d}:{mi:02d}"


# ============================================================
#                    价格 slots → 48 点
# ============================================================


def slots_to_48(slots: Optional[dict]) -> List[float]:
    """数据库价格 slots（{time_label: value | {v2: value}}） → 48 点 list。

    缺槽位补 0.0；item 为 dict 时取 v2（日前/实时曲线），否则取本身。
    """
    res = [0.0] * 48
    if not slots:
        return res
    for i in range(48):
        tl = idx_to_time_label(i)
        item = slots.get(tl)
        if item:
            res[i] = item.get("v2") if isinstance(item, dict) else item
    return res


# ============================================================
#                    公共加载
# ============================================================


def prepare_common(
    node_name: str,
    start_date_str: str,
    end_date_str: str,
    qty_year: float,
    qty_month: float,
    qty_tenday1: float,
    qty_tenday2: float,
    qty_tenday3: float,
) -> dict:
    """两个 builder 共用的数据准备：

    1) 解析日期范围；
    2) 调用分解引擎并按日期展开为 {date: {year/month/tendayX: [48点]}}；
    3) 拉取合约数据（未拆分）+ 节点日前/实时 + 统一结算点日前。

    返回 dict，builder 只需在此基础上组装自己的返回结构。
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    y, m = start_date.year, start_date.month

    # 延迟导入避免与 api / contract_service 形成循环
    from services.bid_space_service import fetch_day_ahead_range, fetch_realtime_range
    from services.db_store import fetch_contract_data
    from services.contract_service import generate_contract_decomposition

    decomp_result = generate_contract_decomposition(
        y, m, qty_year, qty_month, qty_tenday1, qty_tenday2, qty_tenday3
    )
    decomp_by_date: Dict[str, Dict[str, List[float]]] = {}
    for key in ("year", "month", "tenday1", "tenday2", "tenday3"):
        for day_data in decomp_result.get(key, []):
            d_str = f"{y}-{day_data['date']}"
            decomp_by_date.setdefault(d_str, {})[key] = day_data["points"]

    c_rows = list(fetch_contract_data(node_name, start_date_str, end_date_str) or [])
    node_day = fetch_day_ahead_range(start_date_str, end_date_str, node_name)
    node_rt = fetch_realtime_range(start_date_str, end_date_str, node_name)
    unified_day = fetch_day_ahead_range(start_date_str, end_date_str)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "y": y,
        "m": m,
        "decomp_by_date": decomp_by_date,
        "c_rows": c_rows,
        "node_day": node_day,
        "node_rt": node_rt,
        "unified_day": unified_day,
    }


# ============================================================
#                    c_rows 分类聚合
# ============================================================


def _aggregate_by_type(c_rows, data_type: str) -> Dict[str, List[float]]:
    result: Dict[str, List[float]] = {}
    for r in c_rows:
        if str(r["data_type"]) != data_type:
            continue
        d = str(r["date"])[:10]
        idx = time_label_to_idx(str(r["time_label"]))
        if idx != -1:
            result.setdefault(d, [0.0] * 48)[idx] += float(r["value"])
    return result


def aggregate_actual_by_date(c_rows) -> Dict[str, List[float]]:
    """从 c_rows 提取 actual 类型，按 date 聚合为 48 点。"""
    return _aggregate_by_type(c_rows, "actual")


def aggregate_year_by_date(c_rows) -> Dict[str, List[float]]:
    """从 c_rows 提取 year 类型，按 date 聚合为 48 点。"""
    return _aggregate_by_type(c_rows, "year")


def _fetch_merged_prices(start_date, end_date, point_type, price_type, unit_name=None):
    """先查江苏库，命中即清理浙江库，最后合并返回"""
    query_unit = unit_name if point_type == "plant" else None
    if price_type == "day_ahead":
        js_map = fetch_day_ahead_range(start_date, end_date, query_unit)
    else:
        js_map = fetch_realtime_range(start_date, end_date, query_unit)

    js_dates = set(js_map.keys())
    if js_dates:
        for d in js_dates:
            try:
                clear_price(d, point_type, price_type, query_unit)
            except Exception:
                pass

    zj_rows = fetch_price_range(
        start_date, end_date, point_type, price_type, query_unit
    )
    for r in zj_rows:
        d = str(r["date"])
        if d in js_dates:  # 江苏库有，跳过
            continue
        if d not in js_map:
            js_map[d] = {}
        js_map[d][r["time_label"]] = {"v2": r["value"]}

    return js_map
