import os

from flask import Blueprint, request
from services.storage_config import StorageConfig
from services.cleanup_task import get_cleanup_task
from services.temp_manager import TempManager
from utils.response import success, fail

temp_bp = Blueprint("temp_data", __name__)


@temp_bp.get("/config")
def get_config():
    """返回当前临时数据根目录"""
    return success({"tempDir": StorageConfig.get_temp_dir()})


@temp_bp.post("/config")
def update_config():
    """
    切换临时数据根目录
    body: { tempDir: string, migrate?: boolean }
    """
    data = request.get_json(silent=True) or {}
    new_path = data.get("tempDir")
    migrate = bool(data.get("migrate", False))

    result = StorageConfig.set_temp_dir(new_path, migrate=migrate)
    if not result["ok"]:
        return fail(result["error"])

    return success(
        result,
        msg=f"存储目录已切换（迁移 {result['migrated']}，跳过 {result['skipped']}）",
    )


def _handle_single(upload_file, data_type, sub_type, date, node_name):
    """处理单个文件，返回 { ok, name, path?, dates?, devices?, error? }"""
    filename = upload_file.filename or ""

    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xls"):
        return {"ok": False, "name": filename, "error": "仅支持 .xlsx / .xls 文件"}

    # ========================================================
    # ① 负荷 / 光伏：原样保存 + 解析日期/设备
    # ========================================================
    if data_type in ("load", "pv"):
        from services.load_parser import (
            parse_load_excel,
            detect_kind_from_filename,
        )

        raw_kind = detect_kind_from_filename(filename)
        actual_data_type = "pv" if raw_kind in ("pv", "pv_forecast") else "load"

        try:
            path = TempManager.save_raw(upload_file, actual_data_type)
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"保存失败: {e}"}

        try:
            items = parse_load_excel(path, kind=raw_kind)
        except Exception:
            items = []

        return {
            "ok": True,
            "name": filename,
            "path": os.path.relpath(path, TempManager.base_dir()).replace("\\", "/"),
            "dates": sorted({it["date"] for it in items}),
            "devices": sorted({it["device"] for it in items if it["device"]}),
            "count": len(items),
        }

    # ========================================================
    # ② 日前电价 · 统一结算点：原样保存 + 解析日期
    # ========================================================
    if data_type == "day-ahead" and sub_type == "unified":
        try:
            path = TempManager.save_raw(upload_file, "day-ahead", "unified")
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"保存失败: {e}"}

        from services.day_ahead_parser import parse_unified_price_excel

        try:
            items = parse_unified_price_excel(path)
        except Exception:
            items = []

        return {
            "ok": True,
            "name": filename,
            "path": os.path.relpath(path, TempManager.base_dir()).replace("\\", "/"),
            "dates": sorted({it["date"] for it in items}),
            "count": len(items),
        }

    # ---------- 价差分析 · 电厂节点：分发到 spread/plant ----------
    if data_type == "spread" and sub_type == "plant":
        from services.day_ahead_service import (
            _uploads_temp_dir,
            import_plant_price_file,
            write_plant_node_data,
        )
        from services.node_manager import NodeManager

        registered = set(NodeManager.names())
        if not registered:
            return {
                "ok": False,
                "name": filename,
                "error": "尚未录入任何节点，请先在「节点编辑」中添加节点",
            }

        tmp_dir = _uploads_temp_dir()
        tmp_path = os.path.join(tmp_dir, filename)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        upload_file.save(tmp_path)

        try:
            grouped = import_plant_price_file(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        if not grouped:
            return {"ok": False, "name": filename, "error": "文件未解析到有效节点数据"}

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

        written_nodes = []
        written_dates = set()
        for name, day_items in matched.items():
            ok_any = False
            for it in day_items:
                if write_plant_node_data(
                    name, it["date"], it["raw"], base_subdir="spread/plant"
                ):
                    ok_any = True
                    written_dates.add(it["date"])
            if ok_any:
                written_nodes.append(name)

        if not written_nodes:
            return {"ok": False, "name": filename, "error": "写入实时节点数据失败"}

        return {
            "ok": True,
            "name": filename,
            "nodes": sorted(written_nodes),
            "dates": sorted(written_dates),
            "ignoredNodes": ignored,
            "count": len(written_dates) * len(written_nodes),
        }

    # ========================================================
    # ③ 日前电价 · 电厂节点：解析文件 → 分发到各已录入节点
    # ========================================================
    if data_type == "day-ahead" and sub_type == "plant":
        from services.day_ahead_service import (
            _uploads_temp_dir,
            import_plant_price_file,
            write_plant_node_data,
        )
        from services.node_manager import NodeManager

        registered = set(NodeManager.names())
        if not registered:
            return {
                "ok": False,
                "name": filename,
                "error": "尚未录入任何节点，请先在「节点编辑」中添加节点",
            }

        tmp_dir = _uploads_temp_dir()
        tmp_path = os.path.join(tmp_dir, filename)
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        upload_file.save(tmp_path)

        try:
            grouped = import_plant_price_file(tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        if not grouped:
            return {
                "ok": False,
                "name": filename,
                "error": "文件未解析到有效节点数据",
            }

        matched = {k: v for k, v in grouped.items() if k in registered}
        ignored = sorted(set(grouped.keys()) - registered)

        if not matched:
            preview = "、".join(ignored[:5]) + (" 等" if len(ignored) > 5 else "")
            return {
                "ok": False,
                "name": filename,
                "error": (f"文件中的节点都未在节点编辑中录入。（文件包含：{preview}）"),
                "ignoredNodes": ignored,
            }

        written_nodes = []
        written_dates = set()
        for name, day_items in matched.items():
            ok_any = False
            for it in day_items:
                if write_plant_node_data(name, it["date"], it["raw"]):
                    ok_any = True
                    written_dates.add(it["date"])
            if ok_any:
                written_nodes.append(name)

        if not written_nodes:
            return {
                "ok": False,
                "name": filename,
                "error": "写入节点数据失败",
            }

        return {
            "ok": True,
            "name": filename,
            "nodes": sorted(written_nodes),
            "dates": sorted(written_dates),
            "ignoredNodes": ignored,
            "count": len(written_dates) * len(written_nodes),
        }

    # ========================================================
    # ④ 价差分析 · 实时价格（spread/unified）：原样保存 ← 关键分支
    # ========================================================
    if data_type == "spread" and sub_type == "unified":
        try:
            path = TempManager.save_raw(upload_file, "spread", "unified")
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"保存失败: {e}"}

        from services.day_ahead_parser import parse_real_time_price_excel

        try:
            items = parse_real_time_price_excel(path)
        except Exception:
            items = []

        return {
            "ok": True,
            "name": filename,
            "path": os.path.relpath(path, TempManager.base_dir()).replace("\\", "/"),
            "dates": sorted({it["date"] for it in items}),
            "count": len(items),
        }

    # ========================================================
    # ⑤ 其他：结构化保存（需要 date）
    # ========================================================
    if not date:
        return {"ok": False, "name": filename, "error": "缺少参数 date"}

    try:
        path = TempManager.save(
            upload_file, data_type, sub_type, date, node_name or None
        )
    except Exception as e:
        return {"ok": False, "name": filename, "error": f"保存失败: {e}"}

    return {
        "ok": True,
        "name": filename,
        "path": os.path.relpath(path, TempManager.base_dir()).replace("\\", "/"),
    }


@temp_bp.post("/upload")
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

    # 兼容旧调用（单文件时把结果摊到顶层）
    payload = {"results": results, "total": total, "ok": ok}
    if total == 1:
        payload.update(results[0])

    return success(payload, msg=f"成功上传 {ok}/{total} 个文件")


@temp_bp.get("/list")
def list_files():
    data_type = request.args.get("dataType")
    sub_type = request.args.get("subType")
    date = request.args.get("date")
    node_name = request.args.get("nodeName")

    items = TempManager.list_all()
    if data_type:
        items = [i for i in items if i["dataType"] == data_type]
    if sub_type:
        items = [i for i in items if i["subType"] == sub_type]
    if date:
        items = [i for i in items if i["date"] == date]
    if node_name:
        items = [i for i in items if i["nodeName"] == node_name]

    return success(items)


@temp_bp.post("/delete")
def delete():
    data = request.get_json(silent=True) or {}
    relpath = data.get("path")
    if not relpath:
        return fail("缺少参数 path")

    ok = TempManager.delete_by_relpath(relpath)
    if not ok:
        return fail("删除失败：文件不存在或路径非法")
    return success(msg="已删除")


@temp_bp.post("/scan")
def scan():
    removed = get_cleanup_task().scan_once()
    return success({"removed": removed}, msg=f"本次扫描删除 {removed} 个临时文件")

    # ---------- 价差分析 · 实时价格：原样保存 ----------
    if data_type == "spread" and sub_type == "unified":
        try:
            path = TempManager.save_raw(upload_file, "spread", "unified")
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"保存失败: {e}"}

        from services.day_ahead_parser import parse_real_time_price_excel

        try:
            items = parse_real_time_price_excel(path)
        except Exception:
            items = []

        return {
            "ok": True,
            "name": filename,
            "path": os.path.relpath(path, TempManager.base_dir()).replace("\\", "/"),
            "dates": sorted({it["date"] for it in items}),
            "count": len(items),
        }
