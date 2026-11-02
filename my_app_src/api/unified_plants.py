from flask import Blueprint, request, send_file
import pandas as pd
from io import BytesIO
from services import unified_plant_service as svc
from utils.response import success, fail

unified_plants_bp = Blueprint("unified_plants", __name__)


@unified_plants_bp.post("/import")
def import_excel():
    """导入统调电厂 Excel（覆盖旧数据）"""
    file = request.files.get("file")
    res = svc.save_import(file)
    if not res["ok"]:
        return fail(res["error"])
    return success(res, msg=f"导入成功，共 {res['count']} 条机组数据")


@unified_plants_bp.delete("/import")
def clear_excel():
    res = svc.clear_import()
    if not res["ok"]:
        return fail(res["error"])
    return success(msg="已清空导入数据")


@unified_plants_bp.get("/list")
def list_items():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("pageSize", 20))
    except ValueError:
        page, page_size = 1, 20

    keyword = request.args.get("keyword", "")
    city = request.args.get("city", "")

    data = svc.list_paged(page, page_size, keyword, city)
    return success(data)


@unified_plants_bp.get("/map")
def map_data():
    return success(svc.map_aggregation())


@unified_plants_bp.get("/cities")
def cities():
    return success(svc.city_options())


@unified_plants_bp.get("/template")
def download_template():
    """下载统调电厂导入模板"""
    columns = ["调度命名", "机组序号", "铭牌出力(MW)", "所在城市"]
    sample_data = [
        ["北仑港电厂", "1", 630.0, "宁波市"],
        ["北仑港电厂", "2", 630.0, "宁波市"],
        ["嘉兴发电厂", "1", 300.0, "嘉兴市"],
    ]
    df = pd.DataFrame(sample_data, columns=columns)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="统调电厂数据")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="统调电厂导入模板.xlsx",
    )
