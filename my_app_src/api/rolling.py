from flask import Blueprint, request
from utils.response import success, fail
from services.rolling_analysis import get_rolling_analysis

rolling_bp = Blueprint("rolling", __name__)


@rolling_bp.route("/analysis", methods=["GET"])
def rolling_analysis():
    target_date = request.args.get("targetDate")
    if not target_date:
        return fail("请选择标的日")

    try:
        data = get_rolling_analysis(target_date)
        return success(data)
    except Exception as e:
        return fail(str(e))
