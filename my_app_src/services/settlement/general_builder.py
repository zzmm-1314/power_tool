from datetime import timedelta

from services.settlement._common import (
    prepare_common,
    aggregate_actual_by_date,
    slots_to_48,
    _fetch_merged_prices,
    time_label_to_idx,  # ⭐ 新增导入
)


def build_general_data(
    node_name,
    start_date_str,
    end_date_str,
    qty_year,
    qty_month,
    qty_tenday1,
    qty_tenday2,
    qty_tenday3,
    year_source="decompose",
):
    ctx = prepare_common(
        node_name,
        start_date_str,
        end_date_str,
        qty_year,
        qty_month,
        qty_tenday1,
        qty_tenday2,
        qty_tenday3,
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

    # ⭐ 提取数据库中的合约电量
    db_year_by_date = {}
    db_qty_by_date = {}
    for r in c_rows:
        d = str(r["date"])[:10]
        idx = time_label_to_idx(str(r["time_label"]))  # ⭐ 修复未定义函数
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

        # ⭐ 核心修复：根据 year_source 决定电量来源
        if year_source == "database":
            data["stat"][d_str] = db_year_by_date.get(d_str, [0.0] * 48)

            # 月度
            m = db_qty_by_date.get(d_str, {}).get("month", [0.0] * 48)
            data["strategy_month"][d_str] = (
                m if any(v != 0 for v in m) else day_decomp.get("month", [0.0] * 48)
            )

            # 旬度
            t1 = db_qty_by_date.get(d_str, {}).get("tenday1", [0.0] * 48)
            t2 = db_qty_by_date.get(d_str, {}).get("tenday2", [0.0] * 48)
            t3 = db_qty_by_date.get(d_str, {}).get("tenday3", [0.0] * 48)
            if any(v != 0 for arr in [t1, t2, t3] for v in arr):
                data["strategy_tenday"][d_str] = [
                    t1[i] + t2[i] + t3[i] for i in range(48)
                ]
            else:
                dt1 = day_decomp.get("tenday1", [0.0] * 48)
                dt2 = day_decomp.get("tenday2", [0.0] * 48)
                dt3 = day_decomp.get("tenday3", [0.0] * 48)
                data["strategy_tenday"][d_str] = [
                    dt1[i] + dt2[i] + dt3[i] for i in range(48)
                ]
        else:
            data["stat"][d_str] = day_decomp.get("year", [0.0] * 48)
            data["strategy_month"][d_str] = day_decomp.get("month", [0.0] * 48)
            t1 = day_decomp.get("tenday1", [0.0] * 48)
            t2 = day_decomp.get("tenday2", [0.0] * 48)
            t3 = day_decomp.get("tenday3", [0.0] * 48)
            data["strategy_tenday"][d_str] = [t1[i] + t2[i] + t3[i] for i in range(48)]

        data["info_spot_day"][d_str] = slots_to_48(node_day.get(d_str, {}))
        data["info_spot_rt"][d_str] = slots_to_48(node_rt.get(d_str, {}))
        data["info_contract"][d_str] = slots_to_48(unified_day.get(d_str, {}))

        current += timedelta(days=1)

    return data
