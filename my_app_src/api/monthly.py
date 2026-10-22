"""月报生成 API"""

from flask import Blueprint, request

from services import monthly_service
from utils.response import success, fail

monthly_bp = Blueprint("monthly", __name__)


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
    """上传 PDF，返回字段预览"""
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
    """上传 PDF + 模板名，返回 base64 docx"""
    file = request.files.get("file")
    template_name = (request.form.get("templateName") or "").strip()

    if file is None or not file.filename:
        return fail("未选择 PDF 文件")
    if not file.filename.lower().endswith(".pdf"):
        return fail("仅支持 .pdf 文件")
    if not template_name:
        return fail("未选择模板")

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
