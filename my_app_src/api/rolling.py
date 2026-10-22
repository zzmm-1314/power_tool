"""滚撮分析 API"""

from datetime import datetime

from flask import Blueprint, request, send_file

from services.rolling_analysis import analyze, export_excel
from utils.response import success, fail

rolling_bp = Blueprint("rolling", __name__)


@rolling_bp.post("/analyze")
def rolling_analyze():
    data = request.get_json(silent=True) or {}
    html = (data.get("html") or "").strip()
    try:
        avg_days = int(data.get("avgDays", 3) or 3)
    except (TypeError, ValueError):
        avg_days = 3
    ref_date = (data.get("refDate") or "").strip() or None

    if not html:
        return fail("请粘贴 HTML 片段")
    if avg_days < 1 or avg_days > 60:
        return fail("均值天数需在 1~60 之间")

    try:
        res = analyze(html, avg_days=avg_days, ref_date=ref_date)
    except Exception as e:
        return fail(str(e))

    return success(res)


@rolling_bp.post("/export")
def rolling_export():
    data = request.get_json(silent=True) or {}
    html = (data.get("html") or "").strip()
    try:
        avg_days = int(data.get("avgDays", 3) or 3)
    except (TypeError, ValueError):
        avg_days = 3
    ref_date = (data.get("refDate") or "").strip() or None

    if not html:
        return fail("请粘贴 HTML 片段")

    try:
        output = export_excel(html, avg_days=avg_days, ref_date=ref_date)
    except Exception as e:
        return fail(str(e))

    filename = f"滚撮分析_{avg_days}天_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
