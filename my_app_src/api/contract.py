from flask import Blueprint, request, send_file
from utils.response import success, fail
from services.contract_service import (
    generate_contract_decomposition,
    save_uploaded_file,
    BASE_DIR,
    NODES_DIR,
    ensure_dirs,
)
from io import BytesIO
import pandas as pd
import os

contract_bp = Blueprint("contract", __name__)


# ==================== 模板下载 ====================
@contract_bp.route("/template", methods=["GET"])
def download_template():
    df = pd.DataFrame(
        {
            "日期": ["2026-01-01", "2026-02-17", "2026-10-01"],
            "备注": ["元旦", "春节", "国庆节"],
        }
    )
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="节假日")
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="节假日模板.xlsx",
    )


@contract_bp.route("/actual-template", methods=["GET"])
def download_actual_template():
    columns = ["日期"] + [f"电力点{i}" for i in range(1, 49)]
    sample_data = {"日期": ["2026-10-01"]}
    for i in range(1, 49):
        sample_data[f"电力点{i}"] = [0.0]
    df = pd.DataFrame(sample_data, columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="实际发电量")
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="实际发电量上传模板.xlsx",
    )


# ==================== 配置上传 ====================
@contract_bp.route("/config/base", methods=["POST"])
def upload_base_config():
    ensure_dirs()
    curve_file = request.files.get("curve")
    holiday_file = request.files.get("holiday")
    if curve_file:
        save_uploaded_file(curve_file, os.path.join(BASE_DIR, "typical_curve.xlsx"))
    if holiday_file:
        save_uploaded_file(holiday_file, os.path.join(BASE_DIR, "holidays.xlsx"))
    return success(msg="基础配置保存成功")


@contract_bp.route("/config/node-data", methods=["POST"])
def upload_node_data():
    ensure_dirs()
    node_name = request.form.get("node_name")
    data_type = request.form.get("data_type")  # year, month, tenday1... rolling, actual
    if not node_name or not data_type:
        return fail("缺少节点或数据类型参数")

    files = request.files.getlist("files")
    if not files:
        return fail("未选择文件")

    node_dir = os.path.join(NODES_DIR, node_name, data_type)
    # 清空老文件
    if os.path.exists(node_dir):
        import shutil

        shutil.rmtree(node_dir)
    os.makedirs(node_dir, exist_ok=True)

    for i, f in enumerate(files):
        save_path = os.path.join(node_dir, f"{i}_{f.filename}")
        save_uploaded_file(f, save_path)

    return success(msg=f"{data_type} 数据上传成功")


# ==================== 合约分解计算 ====================
@contract_bp.route("/decompose", methods=["POST"])
def decompose():
    try:
        data = request.get_json(silent=True) or {}
        year = int(data.get("year", 2026))
        month = int(data.get("month", 1))
        qty_year = float(data.get("qty_year", 0))
        qty_month = float(data.get("qty_month", 0))
        qty_tenday1 = float(data.get("qty_tenday1", 0))
        qty_tenday2 = float(data.get("qty_tenday2", 0))
        qty_tenday3 = float(data.get("qty_tenday3", 0))

        result = generate_contract_decomposition(
            year, month, qty_year, qty_month, qty_tenday1, qty_tenday2, qty_tenday3
        )
        return success(result)
    except Exception as e:
        return fail(str(e))


@contract_bp.route("/export", methods=["POST"])
def export_result():
    """将前端传回来的结果数据导出为包含 5 个 Sheet 的 Excel"""
    data = request.get_json(silent=True) or {}
    result_data = data.get("resultData")
    times = data.get("times", [])

    if not result_data or not times:
        return fail("无数据可导出")

    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            sheet_names = {
                "year": "年度分解",
                "month": "月度分解",
                "tenday1": "上旬分解",
                "tenday2": "中旬分解",
                "tenday3": "下旬分解",
            }

            for key, sheet_name in sheet_names.items():
                days_data = result_data.get(key, [])
                if not days_data:
                    continue

                rows = []
                for day in days_data:
                    row_dict = {
                        "日期": day["date"],
                        "类型": day["day_type"],
                        "日电量": day["daily_qty"],
                    }
                    # 展开 48 点
                    for i, t in enumerate(times):
                        row_dict[t] = day["points"][i]
                    rows.append(row_dict)

                df = pd.DataFrame(rows)
                df.to_excel(writer, index=False, sheet_name=sheet_name)

        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="合约分解结果.xlsx",
        )
    except Exception as e:
        return fail(f"导出失败: {str(e)}")
