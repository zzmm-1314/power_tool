from flask import Blueprint, request

from services.data_provider import fetch_data
from services.price_spread_service import (
    fetch_spread_heatmap,
    fetch_spread_plant_heatmap,
    fetch_spread_single_day,
)
from utils.dataframe import df_to_points
from utils.response import success, fail

spread_bp = Blueprint("spread", __name__)


@spread_bp.get("/analysis")
def spread_analysis():
    """单日价差（保留兼容）"""
    date = request.args.get("date")
    node_type = request.args.get("nodeType", "unified")
    node_name = request.args.get("nodeName")

    if not date:
        return fail("缺少参数 date")

    if node_type == "unified":
        data = fetch_spread_single_day(date)
        return success(
            {
                "date": date,
                "nodeType": "unified",
                "source": data["source"],
                "points": data["hourly"],
            }
        )

    if not node_name:
        return fail("电厂节点查询需提供 nodeName")

    df, source, temp_path = fetch_data("spread", node_type, date, node_name)
    return success(
        {
            "date": date,
            "nodeType": node_type,
            "nodeName": node_name,
            "source": source,
            "tempPath": temp_path,
            "points": df_to_points(df, decimals=3),
        }
    )


@spread_bp.get("/unified-heatmap")
def unified_heatmap():
    end_date = request.args.get("endDate")
    start_date = request.args.get("startDate")  # ← 新增
    try:
        days = int(request.args.get("days", 14))
    except ValueError:
        days = 14
    return success(
        fetch_spread_heatmap(end_date=end_date, days=days, start_date=start_date)
    )


@spread_bp.get("/plant-heatmap")
def plant_heatmap():
    node_name = (request.args.get("nodeName") or "").strip()
    if not node_name:
        return fail("缺少参数 nodeName")

    end_date = request.args.get("endDate")
    start_date = request.args.get("startDate")  # ← 新增
    try:
        days = int(request.args.get("days", 14))
    except ValueError:
        days = 14

    return success(
        fetch_spread_plant_heatmap(
            node_name=node_name,
            end_date=end_date,
            days=days,
            start_date=start_date,
        )
    )


@spread_bp.get("/daily-prices")
def daily_prices():
    """单日价格明细：日前 / 实时 / 价差（48 点）"""
    from services.price_spread_service import fetch_spread_daily_prices

    date = request.args.get("date")
    node_type = request.args.get("nodeType", "unified")
    node_name = request.args.get("nodeName")

    if not date:
        return fail("缺少参数 date")
    if node_type == "plant" and not node_name:
        return fail("缺少参数 nodeName")

    return success(
        fetch_spread_daily_prices(
            date=date,
            node_type=node_type,
            node_name=node_name,
        )
    )
