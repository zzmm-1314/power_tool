"""上传接口：Excel 即时解析 → 内存预览 + 尽力入库

设计：
- 文件只写到系统临时目录，解析完立即删除，项目目录不保留副本
- 解析结果先进进程内存预览（页面立刻能显示），同时尽力写入业务数据库
- 数据库不可用时上传依旧成功，仅返回 saved=false 提示未持久化
"""

import os
import shutil
import tempfile
from typing import Dict

from flask import Blueprint, request

from services import preview_store
from services.ingest import store_points
from utils.response import success, fail

upload_bp = Blueprint("upload", __name__)

_EXCEL_EXTS = (".xlsx", ".xls")


def _write_to_sandbox(upload_file) -> str:
    """把上传文件写入系统临时目录（解析后即删，不进项目数据目录）"""
    workdir = tempfile.mkdtemp(prefix="power-tool-upload-")
    safe_name = os.path.basename(upload_file.filename or "upload.xlsx")
    path = os.path.join(workdir, safe_name)
    upload_file.save(path)
    return path


def _cleanup(path: str) -> None:
    try:
        os.remove(path)
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    except OSError:
        pass


def _ingest(
    data_type: str, sub_type: str, device: str, date: str, points: list, filename: str
) -> Dict:
    return store_points(data_type, sub_type, device, date, points, source_file=filename)


def _summary_result(items: list, filename: str, extra: dict = None) -> dict:
    """把逐条入库结果汇总为上传响应"""
    saved_all = all(i.get("saved") for i in items) if items else False
    first_err = next((i.get("dbError") for i in items if i.get("dbError")), "")
    res = {"ok": True, "name": filename, "saved": saved_all}
    if not saved_all and first_err:
        res["dbError"] = first_err
    if extra:
        res.update(extra)
    return res


def _handle_single(upload_file, data_type, sub_type, date, node_name):
    """处理单个文件，返回 { ok, name, dates?, devices?, nodes?, saved?, error? }"""
    filename = upload_file.filename or ""

    ext = os.path.splitext(filename)[1].lower()
    if ext not in _EXCEL_EXTS:
        return {"ok": False, "name": filename, "error": "仅支持 .xlsx / .xls 文件"}

    # ========================================================
    # ① 负荷 / 光伏：解析后按 kind 入库（同维度覆盖）
    # ========================================================
    if data_type in ("load", "pv"):
        from services.load_parser import detect_kind_from_filename, parse_load_excel

        raw_kind = detect_kind_from_filename(filename)
        actual_data_type = "pv" if raw_kind in ("pv", "pv_forecast") else "load"

        path = _write_to_sandbox(upload_file)
        try:
            try:
                items = parse_load_excel(path, kind=raw_kind)
            except Exception as e:
                return {"ok": False, "name": filename, "error": f"解析失败: {e}"}
            if not items:
                return {"ok": False, "name": filename, "error": "未解析到有效数据"}

            stored = []
            for it in items:
                stored.append(
                    _ingest(
                        actual_data_type,
                        it.get("kind", raw_kind),
                        it.get("device", ""),
                        it.get("date", ""),
                        it.get("points") or [],
                        filename,
                    )
                )
        finally:
            _cleanup(path)

        return _summary_result(
            stored,
            filename,
            {
                "dataType": actual_data_type,
                "dates": sorted({it["date"] for it in items}),
                "devices": sorted({it["device"] for it in items if it["device"]}),
                "count": sum(s["preview"] for s in stored),
            },
        )

    # ========================================================
    # ② 日前电价 · 统一结算点
    # ========================================================
    if data_type == "day-ahead" and sub_type == "unified":
        from services.day_ahead_parser import parse_unified_price_excel

        path = _write_to_sandbox(upload_file)
        try:
            try:
                items = parse_unified_price_excel(path)
            except Exception as e:
                return {"ok": False, "name": filename, "error": f"解析失败: {e}"}
            if not items:
                return {"ok": False, "name": filename, "error": "未解析到有效数据"}

            stored = [
                _ingest(
                    "day-ahead",
                    "unified",
                    it.get("device", ""),
                    it["date"],
                    it.get("raw") or [],
                    filename,
                )
                for it in items
            ]
        finally:
            _cleanup(path)

        return _summary_result(
            stored,
            filename,
            {
                "dates": sorted({it["date"] for it in items}),
                "count": sum(s["preview"] for s in stored),
            },
        )

    # ---------- 价差分析 · 电厂节点实时价格 ----------
    if data_type == "spread" and sub_type == "plant":
        return _handle_plant_upload(upload_file, filename, "spread")

    # ========================================================
    # ③ 日前电价 · 电厂节点：按节点分发
    # ========================================================
    if data_type == "day-ahead" and sub_type == "plant":
        return _handle_plant_upload(upload_file, filename, "day-ahead")

    # ========================================================
    # ④ 价差分析 · 实时价格（统一结算点）
    # ========================================================
    if data_type == "spread" and sub_type == "unified":
        from services.day_ahead_parser import parse_real_time_price_excel

        path = _write_to_sandbox(upload_file)
        try:
            try:
                items = parse_real_time_price_excel(path)
            except Exception as e:
                return {"ok": False, "name": filename, "error": f"解析失败: {e}"}
            if not items:
                return {"ok": False, "name": filename, "error": "未解析到有效数据"}

            stored = [
                _ingest(
                    "spread",
                    "unified",
                    it.get("device", ""),
                    it["date"],
                    it.get("raw") or [],
                    filename,
                )
                for it in items
            ]
        finally:
            _cleanup(path)

        return _summary_result(
            stored,
            filename,
            {
                "dates": sorted({it["date"] for it in items}),
                "count": sum(s["preview"] for s in stored),
            },
        )

    # ========================================================
    # ⑤ 其他：按传入 date 取「时间列 + 首个数值列」入库
    # ========================================================
    if not date:
        return {"ok": False, "name": filename, "error": "缺少参数 date"}

    import pandas as pd

    path = _write_to_sandbox(upload_file)
    try:
        try:
            df = pd.read_excel(path, dtype=object)
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"解析失败: {e}"}

        cols = list(df.columns)
        if len(cols) < 2:
            return {"ok": False, "name": filename, "error": "至少需要时间列与数值列"}

        points = []
        for _, row in df.iterrows():
            try:
                v = float(row[cols[-1]])
            except (TypeError, ValueError):
                continue
            points.append({"time": str(row[cols[0]]).strip(), "value": v})

        if not points:
            return {"ok": False, "name": filename, "error": "未解析到有效数据"}

        res = _ingest(data_type, sub_type, node_name or "", date, points, filename)
    finally:
        _cleanup(path)

    return _summary_result([res], filename, {"count": res["preview"]})


def _handle_plant_upload(upload_file, filename: str, data_type: str) -> dict:
    """电厂节点上传：解析 → 只处理已录入节点 → 预览 + 入库"""
    from services.day_ahead_parser import parse_plant_price_excel
    from services.node_manager import NodeManager

    registered = set(NodeManager.names())
    if not registered:
        return {
            "ok": False,
            "name": filename,
            "error": "尚未录入任何节点，请先在「节点编辑」中添加节点",
        }

    path = _write_to_sandbox(upload_file)
    try:
        try:
            items = parse_plant_price_excel(path)
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"解析失败: {e}"}
    finally:
        _cleanup(path)

    if not items:
        return {"ok": False, "name": filename, "error": "文件未解析到有效节点数据"}

    grouped: dict = {}
    for it in items:
        grouped.setdefault(it["device"], []).append(it)

    matched = {k: v for k, v in grouped.items() if k in registered}
    ignored = sorted(set(grouped.keys()) - registered)

    if not matched:
        preview = "、".join(ignored[:5]) + (" 等" if len(ignored) > 5 else "")
        return {
            "ok": False,
            "name": filename,
            "error": f"文件中的节点都未在节点编辑中录入。（文件包含：{preview}）",
            "ignoredNodes": ignored,
        }

    stored: list = []
    written_dates: set = set()
    written_nodes: set = set()
    for name, day_items in matched.items():
        for it in day_items:
            res = _ingest(
                data_type, "plant", name, it["date"], it.get("raw") or [], filename
            )
            stored.append(res)
            written_dates.add(it["date"])
            written_nodes.add(name)

    return _summary_result(
        stored,
        filename,
        {
            "nodes": sorted(written_nodes),
            "dates": sorted(written_dates),
            "ignoredNodes": ignored,
            "count": sum(s["preview"] for s in stored),
        },
    )


@upload_bp.route("", methods=["POST"])
@upload_bp.route("/", methods=["POST"])
@upload_bp.route("/upload", methods=["POST"])
def upload():
    """支持单文件（field=file）与多文件（field=files）上传"""
    upload_list = request.files.getlist("files")
    if not upload_list:
        single = request.files.get("file")
        if single:
            upload_list = [single]

    if not upload_list:
        return fail("未选择文件")

    data_type = (request.form.get("dataType") or "").strip()
    sub_type = (request.form.get("subType") or "").strip()
    date = (request.form.get("date") or "").strip()
    node_name = (request.form.get("nodeName") or "").strip()

    if not data_type:
        return fail("缺少参数 dataType")

    results = [
        _handle_single(f, data_type, sub_type, date, node_name) for f in upload_list
    ]

    ok = sum(1 for r in results if r.get("ok"))
    total = len(results)
    persisted = all(r.get("saved") for r in results if r.get("ok")) if ok else False

    msg = f"已解析 {ok}/{total} 个文件，可即时预览"
    if ok and not persisted:
        msg += "（数据库未连通，数据仅保留在内存，重启后需重新上传）"

    # 兼容旧调用（单文件时把结果摊到顶层）
    payload = {
        "results": results,
        "total": total,
        "ok": ok,
        "saved": persisted,
        "preview": preview_store.summary(),
    }
    if total == 1:
        payload.update(results[0])

    return success(payload, msg=msg)


@upload_bp.get("/preview")
def preview_state():
    """当前内存预览概览（页面刷新后可判断是否还有预览数据）"""
    return success(preview_store.summary())


@upload_bp.delete("/preview")
def clear_preview():
    """清空内存预览（只清预览，不影响已入库数据）"""
    data_type = (request.args.get("dataType") or "").strip() or None
    removed = preview_store.clear(data_type)
    return success({"removed": removed}, msg="已清空内存预览数据")
