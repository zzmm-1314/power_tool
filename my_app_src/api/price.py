from flask import Blueprint, request

from services.data_provider import fetch_data
from services.day_ahead_service import (
    fetch_plant_heatmap,
    fetch_plant_nodes,
    fetch_unified_heatmap,
    fetch_unified_single_day,
)
from utils.dataframe import df_to_points
from utils.response import success, fail

price_bp = Blueprint("price", __name__)


# ---------------- 电厂节点列表 ----------------


@price_bp.get("/plant-nodes")
def plant_nodes():
    """当前临时数据中的所有电厂节点"""
    return success(fetch_plant_nodes())


# ---------------- 日前电价 单日 / 统一结算点 ----------------


@price_bp.get("/day-ahead")
def day_ahead_price():
    date = request.args.get("date")
    node_type = request.args.get("nodeType", "unified")
    node_name = request.args.get("nodeName")

    if not date:
        return fail("缺少参数 date")

    if node_type == "unified":
        data = fetch_unified_single_day(date)
        return success(
            {
                "date": date,
                "nodeType": "unified",
                "source": data["source"],
                "tempPath": None,
                "points": data["hourly"],
                "raw": data["raw"],
            }
        )

    if not node_name:
        return fail("电厂节点查询需提供 nodeName")

    df, source, temp_path = fetch_data("day-ahead", node_type, date, node_name)
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


# ---------------- 统一结算点 热力图 ----------------


@price_bp.get("/day-ahead/unified-heatmap")
def day_ahead_unified_heatmap():
    end_date = request.args.get("endDate")
    start_date = request.args.get("startDate")  # ← 新增
    try:
        days = int(request.args.get("days", 14))
    except ValueError:
        days = 14

    return success(
        fetch_unified_heatmap(end_date=end_date, days=days, start_date=start_date)
    )


# ---------------- 电厂节点 热力图 ----------------


@price_bp.get("/day-ahead/plant-heatmap")
def day_ahead_plant_heatmap():
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
        fetch_plant_heatmap(
            node_name=node_name,
            end_date=end_date,
            days=days,
            start_date=start_date,
        )
    )
