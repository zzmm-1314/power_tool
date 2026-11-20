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

from services.ingest import store_points
from utils.cache import clear_cache
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
    # ① 负荷 / 光伏：解析后按 (data_type, kind) 分组写 tmp_load_pv
    # ========================================================
    if data_type in ("load", "pv"):
        from services.load_parser import detect_kind_from_filename, parse_load_excel
        from services.db_store import save_load_pv

        raw_kind = detect_kind_from_filename(filename)
        path = _write_to_sandbox(upload_file)
        try:
            try:
                items = parse_load_excel(path, kind=raw_kind)
            except Exception as e:
                return {"ok": False, "name": filename, "error": f"解析失败: {e}"}
            if not items:
                return {"ok": False, "name": filename, "error": "未解析到有效数据"}

            # it["kind"] ∈ {actual, forecast, pv, pv_forecast}
            # 映射到 (data_type, kind)
            def _map(k: str):
                if k == "actual":
                    return "load", "actual"
                if k == "forecast":
                    return "load", "forecast"
                if k == "pv":
                    return "pv", "actual"
                if k == "pv_forecast":
                    return "pv", "forecast"
                return "load", "actual"

            groups: dict = {}
            for it in items:
                dt, kd = _map(it.get("kind", raw_kind))
                groups.setdefault((dt, kd), []).append(it)

            saved = []
            for (dt, kd), group_items in groups.items():
                records = []
                for it in group_items:
                    for i, pt in enumerate(it.get("points") or []):
                        records.append(
                            {
                                "date": it["date"],
                                "unit_name": it.get("device", "") or "浙江电网",
                                "time_label": pt["time"],
                                "seq": i,
                                "value": pt["value"],
                            }
                        )
                try:
                    cnt = save_load_pv(records, dt, kd)
                    saved.append(cnt)
                except Exception as e:
                    return {"ok": False, "name": filename, "error": f"入库失败: {e}"}
        finally:
            _cleanup(path)

        return _summary_result(
            [{"preview": sum(saved), "saved": True, "dbError": ""}],
            filename,
            {
                "dataType": data_type,
                "dates": sorted({it["date"] for it in items}),
                "devices": sorted(
                    {it.get("device") for it in items if it.get("device")}
                ),
                "count": sum(saved),
            },
        )

    # ========================================================
    # ② 价格（日前/实时 × 统一结算点/节点）→ tmp_price
    # ========================================================
    if data_type in ("day-ahead", "spread") and sub_type in ("unified", "plant"):
        from services.day_ahead_parser import (
            parse_plant_price_excel,
            parse_real_time_price_excel,
            parse_unified_price_excel,
        )
        from services.db_store import save_price

        path = _write_to_sandbox(upload_file)
        try:
            if sub_type == "unified":
                items = (
                    parse_unified_price_excel(path)
                    if data_type == "day-ahead"
                    else parse_real_time_price_excel(path)
                )
            else:
                items = parse_plant_price_excel(path)
        finally:
            _cleanup(path)

        if not items:
            return {"ok": False, "name": filename, "error": "未解析到有效数据"}

        point_type = sub_type  # unified / plant
        price_type = "day_ahead" if data_type == "day-ahead" else "realtime"

        # ⭐ 修复1：如果前端指定了节点，只保留指定节点（极大减少入库量）
        target_nodes = [n.strip() for n in node_name.split(",")] if node_name else None

        # ⭐ 修复2：全量收集 records，不再按节点循环调 save_price（避免几百次建连）
        records = []
        matched_devices = set()
        for it in items:
            device = it.get("device", "")
            if target_nodes and device not in target_nodes:
                continue
            matched_devices.add(device)
            for i, pt in enumerate(it.get("raw") or []):
                records.append(
                    {
                        "date": it["date"],
                        "unit_name": device,
                        "time_label": pt["time"],
                        "seq": i,
                        "value": pt["value"],
                    }
                )

        if not records:
            return {
                "ok": False,
                "name": filename,
                "error": "未匹配到指定节点（或文件中无此节点）",
            }

        # 一次性入库，内部按 (date, unit_name) 分组覆盖
        try:
            cnt = save_price(records, point_type, price_type)
        except Exception as e:
            return {"ok": False, "name": filename, "error": f"入库失败: {e}"}

        return _summary_result(
            [{"preview": cnt, "saved": True, "dbError": ""}],
            filename,
            {
                "dataType": f"{data_type}-{sub_type}",
                "dates": sorted({it["date"] for it in items}),
                "nodes": sorted(matched_devices),
                "count": cnt,
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

    # 有新数据落库时清空读取缓存（日前/价差/江苏库查询均为长 TTL 缓存），
    # 否则紧接着的「查询」会命中旧缓存，看起来像没读到新上传的数据。
    if ok:
        clear_cache()

    msg = f"已解析 {ok}/{total} 个文件，可即时预览"
    if ok and not persisted:
        msg += "（数据库未连通，数据仅保留在内存，重启后需重新上传）"

    # 兼容旧调用（单文件时把结果摊到顶层）
    payload = {
        "results": results,
        "total": total,
        "ok": ok,
        "saved": persisted,
    }
    if total == 1:
        payload.update(results[0])

    return success(payload, msg=msg)
