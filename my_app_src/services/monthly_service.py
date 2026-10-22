"""月报生成服务：模板管理 + PDF 解析 + Word 渲染"""

import base64
import io
import os
import tempfile
from datetime import datetime
from typing import Dict, List

from docxtpl import DocxTemplate

from services.temp_manager import TempManager
from utils.pdf_parser import (
    FIELDS_META,
    build_sheets,
    extract_data,
)

# ==================== 目录 ====================


def _monthly_root() -> str:
    d = os.path.join(TempManager.base_dir(), "monthly")
    os.makedirs(d, exist_ok=True)
    return d


def _template_dir() -> str:
    d = os.path.join(_monthly_root(), "templates")
    os.makedirs(d, exist_ok=True)
    return d


# ==================== 模板管理 ====================


def list_templates() -> List[Dict]:
    d = _template_dir()
    result = []
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".docx"):
            continue
        fp = os.path.join(d, fn)
        stat = os.stat(fp)
        result.append(
            {
                "name": fn,
                "size": stat.st_size,
                "uploadedAt": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
        )
    return result


def save_template(file_storage) -> Dict:
    if file_storage is None or not file_storage.filename:
        return {"ok": False, "error": "未选择文件"}
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext != ".docx":
        return {"ok": False, "error": "仅支持 .docx 文件"}

    name = os.path.basename(file_storage.filename)
    name = name.replace("/", "_").replace("\\", "_")
    path = os.path.join(_template_dir(), name)
    file_storage.save(path)
    return {"ok": True, "name": name, "path": path}


def delete_template(name: str) -> Dict:
    name = os.path.basename(name or "")
    if not name:
        return {"ok": False, "error": "缺少文件名"}
    path = os.path.join(_template_dir(), name)
    if not os.path.exists(path):
        return {"ok": False, "error": "模板不存在"}
    os.remove(path)
    return {"ok": True}


# ==================== PDF 解析 ====================


def _parse_pdf_bytes(pdf_bytes: bytes, original_filename: str) -> Dict:
    """解析 PDF 字节流，返回原始 data 字典"""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        sheets = build_sheets(tmp_path)
        data = extract_data(sheets, original_filename)
        return {"ok": True, "data": data}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"ok": False, "error": f"PDF 解析失败：{e}"}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _json_safe(data: Dict) -> Dict:
    """把特殊类型转为 JSON 可序列化的普通类型"""
    result = {}
    for k, v in data.items():
        if v is None:
            result[k] = ""
        elif isinstance(v, str):
            result[k] = str(v)
        elif isinstance(v, (int, float, bool)):
            result[k] = v
        else:
            result[k] = str(v)
    return result


def parse_pdf_preview(pdf_bytes: bytes, original_filename: str) -> Dict:
    """解析并返回预览（JSON safe）"""
    res = _parse_pdf_bytes(pdf_bytes, original_filename)
    if not res["ok"]:
        return res

    data = res["data"]
    fields = [
        {
            "key": k,
            "label": FIELDS_META[k],
            "value": "" if data.get(k) in (None, "") else str(data.get(k)),
        }
        for k in FIELDS_META
    ]

    return {
        "ok": True,
        "fields": fields,
        "raw": _json_safe(data),
    }


# ==================== 渲染 Word ====================


def render_docx(
    template_name: str,
    pdf_bytes: bytes,
    original_filename: str,
) -> Dict:
    if not template_name:
        return {"ok": False, "error": "未选择模板"}

    template_path = os.path.join(_template_dir(), os.path.basename(template_name))
    if not os.path.exists(template_path):
        return {"ok": False, "error": f"模板不存在：{template_name}"}

    # 1) 解析 PDF
    res = _parse_pdf_bytes(pdf_bytes, original_filename)
    if not res["ok"]:
        return res
    data = res["data"]

    # 2) 渲染
    try:
        tpl = DocxTemplate(template_path)
        tpl.render(data)
        out = io.BytesIO()
        tpl.save(out)
        out.seek(0)
        docx_bytes = out.read()
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"ok": False, "error": f"Word 渲染失败：{e}"}

    # 3) 构造文件名
    report_month = data.get("report_month") or ""
    plant = data.get("plant_name") or ""
    if report_month and plant:
        filename = f"电力交易服务月报_{plant}_{report_month}.docx"
    elif report_month:
        filename = f"电力交易服务月报_{report_month}.docx"
    else:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"电力交易服务月报_{ts}.docx"

    return {
        "ok": True,
        "filename": filename,
        "base64": base64.b64encode(docx_bytes).decode("ascii"),
        "reportMonth": report_month,
        "plantName": plant,
    }
