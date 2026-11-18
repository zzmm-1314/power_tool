"""月报生成 API"""

import json
import re
from flask import Blueprint, request, send_file
from io import BytesIO
import pandas as pd
from services import monthly_service
from utils.response import success, fail
from services.pdf_extract_service import extract_pdf_data, _parse_month

monthly_bp = Blueprint("monthly", __name__)


def _extract_tables_from_request(req) -> tuple[list | None, str]:
    """从请求中取 tables 和 filename。返回 (tables_or_None, filename)"""
    # JSON body（新前端推荐）
    if req.is_json:
        payload = req.get_json(silent=True) or {}
        return payload.get("tables"), payload.get("filename", "")

    # multipart form（兼容：tables 以字符串字段传）
    tables_str = req.form.get("tables")
    if tables_str:
        try:
            return json.loads(tables_str), req.form.get("filename", "")
        except json.JSONDecodeError:
            return None, ""

    return None, ""


# ==================== 模板管理 ====================


@monthly_bp.get("/templates")
def list_templates():
    return success(monthly_service.list_templates())


@monthly_bp.post("/templates")
def upload_template():
    file = request.files.get("file")
    res = monthly_service.save_template(file)
    if not res["ok"]:
        return fail(res["error"])
    return success({"name": res["name"]}, msg="模板已上传")


@monthly_bp.delete("/templates/<path:name>")
def delete_template(name: str):
    res = monthly_service.delete_template(name)
    if not res["ok"]:
        return fail(res["error"])
    return success(msg="已删除")


# ==================== PDF 解析预览 ====================


@monthly_bp.post("/parse")
def parse_pdf():
    tables, filename = _extract_tables_from_request(request)

    # === 新路径：前端传结构化表格 ===
    if tables is not None:
        if not filename:
            f = request.files.get("file")
            filename = f.filename if f else "unknown.pdf"
        res = monthly_service.parse_pdf_preview_from_tables(tables, filename)
        if not res["ok"]:
            return fail(res["error"])
        return success({"fields": res["fields"], "raw": res["raw"]})

    # === 老路径：上传文件 ===
    file = request.files.get("file")
    if file is None or not file.filename:
        return fail("未选择 PDF 文件")
    if not file.filename.lower().endswith(".pdf"):
        return fail("仅支持 .pdf 文件")
    pdf_bytes = file.read()
    res = monthly_service.parse_pdf_preview(pdf_bytes, file.filename)
    if not res["ok"]:
        return fail(res["error"])
    return success({"fields": res["fields"], "raw": res["raw"]})


# ==================== 生成月报 ====================


@monthly_bp.post("/generate")
def generate():
    tables, filename = _extract_tables_from_request(request)
    template_name = (
        request.form.get("templateName")
        or (request.json.get("templateName") if request.is_json else "")
        or ""
    ).strip()

    if not template_name:
        return fail("未选择模板")

    # === 新路径 ===
    if tables is not None:
        if not filename:
            f = request.files.get("file")
            filename = f.filename if f else "unknown.pdf"
        res = monthly_service.render_docx_from_tables(template_name, tables, filename)
    else:
        # === 老路径 ===
        file = request.files.get("file")
        if file is None or not file.filename:
            return fail("未选择 PDF 文件")
        if not file.filename.lower().endswith(".pdf"):
            return fail("仅支持 .pdf 文件")
        pdf_bytes = file.read()
        res = monthly_service.render_docx(template_name, pdf_bytes, file.filename)

    if not res["ok"]:
        return fail(res["error"])

    return success(
        {
            "filename": res["filename"],
            "base64": res["base64"],
            "reportMonth": res["reportMonth"],
            "plantName": res["plantName"],
        },
        msg="生成成功",
    )


@monthly_bp.route("/extract-pdf", methods=["POST"])
def extract_pdf():
    try:
        files = request.files.getlist("files")
        fields_str = request.form.get("fields", "{}")
        fields = json.loads(fields_str)
        if not files:
            return fail("未接收到文件")

        results = []
        for f in files:
            fname = f.filename
            month = _parse_month(fname)
            rec = {"filename": fname, "month": month, "status": "success"}
            try:
                file_bytes = f.read()
                data = extract_pdf_data(file_bytes, fields)
                rec.update(data)
                if not data:
                    rec["status"] = "failed"
            except Exception as e:
                rec["status"] = "failed"
                rec["msg"] = str(e)
            results.append(rec)

        results.sort(key=lambda x: x["month"])
        return success(results)
    except Exception as e:
        return fail(str(e))


@monthly_bp.route("/export-excel", methods=["POST"])
def export_excel():
    """接收前端提取结果，生成并返回 Excel 文件流"""
    data = request.get_json(silent=True) or {}
    results = data.get("results", [])

    if not results:
        return fail("无数据可导出")

    try:
        df = pd.DataFrame(results)

        # 按月份排序
        if "month" in df.columns:
            df = df.sort_values("month", kind="stable")

        # 剔除全为空值的列（如果用户没勾选某些字段）
        df = df.dropna(axis=1, how="all")

        # 重命名列名，让导出的 Excel 更直观
        column_mapping = {
            "filename": "文件名",
            "month": "月份",
            "page1_total_qty": "合计电量",
            "page1_total_price": "合计电价",
            "page2_dayahead_qty": "日前电量",
            "page2_dayahead_price": "日前电价",
            "page2_realtime_qty": "实时电量",
            "page2_realtime_price": "实时电价",
            "status": "状态",
            "msg": "错误信息",
        }
        df = df.rename(columns=column_mapping)

        # 状态转中文
        if "状态" in df.columns:
            df["状态"] = df["状态"].apply(
                lambda x: "成功" if x == "success" else "失败"
            )

        # 写入内存
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="提取结果")
        output.seek(0)

        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="结算单PDF提取结果.xlsx",
        )

    except Exception as e:
        return fail(f"导出失败: {str(e)}")


@monthly_bp.route("/export-page2-excel", methods=["POST"])
def export_page2_excel():
    """接收前端传来的第二页二维数组，导出为多个 Sheet 的 Excel"""
    data = request.get_json(silent=True) or {}
    page2_list = data.get("page2_list", [])

    if not page2_list:
        return fail("无第二页数据可导出")

    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for idx, item in enumerate(page2_list):
                filename = item.get("filename", f"文件{idx+1}")
                table_data = item.get("data", [])
                if not table_data:
                    continue

                # 清理 Sheet 名（最长 31 字符，且不能包含特殊字符）
                sheet_name = re.sub(r"[\\/*?:\[\]]", "", filename)[:25]
                if not sheet_name:
                    sheet_name = f"Sheet{idx+1}"

                df = pd.DataFrame(table_data)
                df.to_excel(writer, index=False, header=False, sheet_name=sheet_name)

        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="第二页完整表格.xlsx",
        )
    except Exception as e:
        return fail(f"导出失败: {str(e)}")
