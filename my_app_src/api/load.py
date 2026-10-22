from flask import Blueprint, request

from services.load_parser import TARGET_DEVICE
from services.load_service import (
    fetch_load_data,
    fetch_load_range,
    fetch_pv_data,
    fetch_pv_range,
)
from utils.response import success, fail

load_bp = Blueprint("load", __name__)


@load_bp.get("/analysis")
def load_analysis():
    date = request.args.get("date")
    start = request.args.get("startDate")
    end = request.args.get("endDate")

    # 范围优先
    if start and end:
        return success(fetch_load_range(start, end))

    # 单日（兼容旧调用）
    if date:
        data = fetch_load_data(date)
        for s in data["series"]:
            s["date"] = date
        return success(data)

    return fail("缺少参数 date 或 startDate/endDate")


@load_bp.get("/devices")
def load_devices():
    """当前系统只展示浙江电网"""
    return success([TARGET_DEVICE])


@load_bp.get("/pv")
def pv_analysis():
    date = request.args.get("date")
    start = request.args.get("startDate")
    end = request.args.get("endDate")

    if start and end:
        return success(fetch_pv_range(start, end))

    if date:
        data = fetch_pv_data(date)
        for s in data["series"]:
            s["date"] = date
        return success(data)

    return fail("缺少参数 date 或 startDate/endDate")
