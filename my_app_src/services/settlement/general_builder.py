from datetime import timedelta

from services.settlement._common import (
    prepare_common,
    aggregate_actual_by_date,
    slots_to_48,
    _fetch_merged_prices,
    time_label_to_idx,  # ⭐ 新增导入
)

# 合约电量五个组成部分：勾选即调用合约分解接口，不勾选取数据库已录入
CONTRACT_PARTS = ("year", "month", "tenday1", "tenday2", "tenday3")
_DB_PART_TYPES = {
    "month": ("month",),
    "tenday1": ("tenday1",),
    "tenday2": ("tenday2",),
    "tenday3": ("tenday3",),
}


def build_general_data(
    node_name,
    start_date_str,
    end_date_str,
    qty_year,
    qty_month,
    qty_tenday1,
    qty_tenday2,
    qty_tenday3,
    contract_sources=None,
):
    """生成模拟结算单所需数据。

    contract_sources: {'year'|'month'|'tenday1'|'tenday2'|'tenday3': 'decompose'|'database'}
    - 'decompose'：该项调用合约分解接口，使用前端输入电量分解结果
    - 'database'：该项直接取数据库已录入的合约电量，不调用分解接口
    五项都为 'database' 时完全不调用分解引擎。
    """
    sources = _normalize_sources(contract_sources)
    need_decompose = any(v == "decompose" for v in sources.values())

    ctx = prepare_common(
        node_name,
        start_date_str,
        end_date_str,
        qty_year,
        qty_month,
        qty_tenday1,
        qty_tenday2,
        qty_tenday3,
        need_decompose=need_decompose,
    )
    start_date = ctx["start_date"]
    end_date = ctx["end_date"]
    decomp_by_date = ctx["decomp_by_date"]
    c_rows = ctx["c_rows"]  # ⭐ 修复未定义变量

    node_day = _fetch_merged_prices(
        start_date_str, end_date_str, "plant", "day_ahead", node_name
    )
    node_rt = _fetch_merged_prices(
        start_date_str, end_date_str, "plant", "realtime", node_name
    )
    unified_day = _fetch_merged_prices(
        start_date_str, end_date_str, "unified", "day_ahead"
    )

    actual_by_date = aggregate_actual_by_date(c_rows)

    data = {
        "spot": {},
        "stat": {},
        "strategy_month": {},
        "strategy_tenday": {},
        "info_spot_day": {},
        "info_spot_rt": {},
        "info_contract": {},
    }

    # ⭐ 提取数据库中的合约电量（按 data_type 分开保存，便于逐项开关）
    db_year_by_date = {}
    db_qty_by_date = {}
    for r in c_rows:
        d = str(r["date"])[:10]
        idx = time_label_to_idx(str(r["time_label"]))
        if idx != -1:
            dtype = str(r["data_type"])
            if dtype == "year":
                db_year_by_date.setdefault(d, [0.0] * 48)[idx] += float(r["value"])
            elif dtype in ("month", "tenday1", "tenday2", "tenday3"):
                db_qty_by_date.setdefault(d, {}).setdefault(dtype, [0.0] * 48)[
                    idx
                ] += float(r["value"])

    current = start_date
    while current <= end_date:
        d_str = current.strftime("%Y-%m-%d")
        day_decomp = decomp_by_date.get(d_str, {})

        data["spot"][d_str] = actual_by_date.get(d_str, [0.0] * 48)

        # 年度：勾选取分解结果，不勾选取数据库
        data["stat"][d_str] = _pick_points(
            sources["year"],
            day_decomp.get("year"),
            db_year_by_date.get(d_str),
        )

        # 月度
        data["strategy_month"][d_str] = _pick_points(
            sources["month"],
            day_decomp.get("month"),
            db_qty_by_date.get(d_str, {}).get("month"),
        )

        # 旬度：上/中/下旬各自判断后相加
        tenday_total = [0.0] * 48
        for part in ("tenday1", "tenday2", "tenday3"):
            part_pts = _pick_points(
                sources[part],
                day_decomp.get(part),
                db_qty_by_date.get(d_str, {}).get(part),
            )
            tenday_total = [tenday_total[i] + part_pts[i] for i in range(48)]
        data["strategy_tenday"][d_str] = tenday_total

        data["info_spot_day"][d_str] = slots_to_48(node_day.get(d_str, {}))
        data["info_spot_rt"][d_str] = slots_to_48(node_rt.get(d_str, {}))
        data["info_contract"][d_str] = slots_to_48(unified_day.get(d_str, {}))

        current += timedelta(days=1)

    return data


def _normalize_sources(contract_sources) -> dict:
    """把前端开关归一为 {'year': 'decompose'|'database', ...}。

    兼容三种入参：
    - None / 空：视为全部取数据库（不调用分解接口）
    - 旧参数 year_source='decompose'：五项都按分解
    - dict：逐项判断，值为 'decompose' 或 True 视为勾选
    """
    if not contract_sources:
        return {part: "database" for part in CONTRACT_PARTS}

    if isinstance(contract_sources, str):
        # 兼容旧的 year_source 单一字符串
        mode = "decompose" if contract_sources == "decompose" else "database"
        return {part: mode for part in CONTRACT_PARTS}

    sources = {}
    for part in CONTRACT_PARTS:
        val = contract_sources.get(part)
        if isinstance(val, bool):
            sources[part] = "decompose" if val else "database"
        else:
            sources[part] = "decompose" if str(val or "").lower() in (
                "decompose",
                "true",
                "1",
            ) else "database"
    return sources


def _pick_points(mode: str, decomp_points, db_points):
    """按来源取 48 点：勾选优先分解结果，未勾选取数据库，均缺省补 0"""
    if mode == "decompose" and decomp_points:
        return decomp_points
    if db_points:
        return db_points
    return [0.0] * 48