from flask import Blueprint, request
from utils.response import success, fail
from services.spot_profit import compute_cross_province_profit

cross_bp = Blueprint("cross_province", __name__)


@cross_bp.route("/spot-analysis", methods=["GET"])
def spot_analysis():
    unit_name = request.args.get("node")
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")

    if not unit_name or not start_date or not end_date:
        return fail("缺少参数 node / startDate / endDate")

    # 口径统一到 services.spot_profit（与模拟结算单共用）
    try:
        result = compute_cross_province_profit(unit_name, start_date, end_date)
    except Exception as e:
        return fail(str(e))
    return success(result)