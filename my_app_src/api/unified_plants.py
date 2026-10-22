from flask import Blueprint, request

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
