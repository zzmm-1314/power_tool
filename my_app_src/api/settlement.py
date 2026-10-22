"""结算单更新 API 蓝图"""

import os
from flask import Blueprint, request

from services.settlement import start_task, get_task
from services.settlement.path_parser import parse_paths_from_files
from utils.response import success, fail

settlement_bp = Blueprint("settlement", __name__)


@settlement_bp.post("/start/<task_type>")
def start(task_type: str):
    """启动结算任务
    支持 task_type: actual / jiaojiang / xiandai
    """
    if task_type not in ("actual", "jiaojiang", "xiandai"):
        return fail(f"不支持的任务类型: {task_type}")

    data = request.get_json(silent=True) or {}
    params = data.get("params") or {}

    # 快速字段校验
    required = {
        "actual": ["folder", "target_file"],
        "jiaojiang": [
            "folder",
            "fixed_file",
            "strategy_file",
            "stat_file",
            "info_file",
            "target_file",
            "annual_price",
            "tenday_early",
            "tenday_mid",
            "tenday_late",
        ],
        "xiandai": [
            "spot_file",
            "stat_file",
            "strategy_file",
            "info_spot_file",
            "info_contract_file",
            "target_file",
            "annual_price",
            "monthly_price",
            "tenday_early",
            "tenday_mid",
            "tenday_late",
        ],
    }[task_type]

    for k in required:
        v = params.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            return fail(f"缺少参数 {k}")

    # 路径类参数校验存在性
    for k in required:
        if k.endswith("_file"):
            p = params[k]
            if not os.path.isfile(p):
                return fail(f"文件不存在: {p}")
        elif k == "folder":
            if not os.path.isdir(params["folder"]):
                return fail(f"文件夹不存在: {params['folder']}")

    try:
        task_id = start_task(task_type, params)
    except Exception as e:
        return fail(f"启动失败: {e}")

    return success({"taskId": task_id}, msg="任务已启动")


@settlement_bp.get("/tasks/<task_id>")
def task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        return fail("任务不存在", code=404), 404
    return success(task)


@settlement_bp.post("/parse-paths")
def parse_paths():
    data = request.get_json(silent=True) or {}
    paths = data.get("paths") or []
    if not paths:
        return fail("未提供路径")

    result = parse_paths_from_files(paths)
    if "error" in result:
        return fail(result["error"])
    return success(result)


@settlement_bp.post("/browse-file")
def browse_file():
    """弹出系统文件选择对话框（需要 GUI 环境）"""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")],
        )
        root.destroy()
        return success({"path": path or ""})
    except Exception as e:
        return fail(f"弹出文件对话框失败：{e}（可能无 GUI 环境）")


@settlement_bp.post("/browse-folder")
def browse_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择文件夹")
        root.destroy()
        return success({"path": path or ""})
    except Exception as e:
        return fail(f"弹出文件夹对话框失败：{e}（可能无 GUI 环境）")


@settlement_bp.post("/build-price-file")
def build_price_file():
    """从数据目录生成结算单所需的「分时价格（现货）」Excel

    body:
    {
      "kind": "unified" | "plant-pair",
      "nodeName": "万华热电",       # kind=plant-pair 时必填
      "startDate": "2026-10-01",
      "endDate": "2026-10-20"
    }
    """
    from services.settlement.price_file_builder import (
        build_plant_pair_file,
        build_unified_file,
    )

    data = request.get_json(silent=True) or {}
    kind = (data.get("kind") or "").strip()
    node_name = (data.get("nodeName") or "").strip()
    start_date = (data.get("startDate") or "").strip()
    end_date = (data.get("endDate") or "").strip()

    if not start_date or not end_date:
        return fail("缺少参数 startDate / endDate")

    if kind == "unified":
        result = build_unified_file(start_date, end_date)
    elif kind == "plant-pair":
        if not node_name:
            return fail("缺少参数 nodeName")
        result = build_plant_pair_file(node_name, start_date, end_date)
    else:
        return fail(f"不支持的类型: {kind}")

    if not result["ok"]:
        return fail(result["error"])

    return success(result, msg="文件已生成")
