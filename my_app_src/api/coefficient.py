"""申报系数预测 API（异步任务 + 进度轮询）"""

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pandas as pd
from flask import Blueprint, request
from services.coefficient.coefficient_config import WEATHER_CONFIG_KEYS
from services.coefficient import coefficient_config as cfg_module
from services.coefficient.data_source import build_gap_df
from services.coefficient.predictor import CoefficientPredictor
from utils.response import success, fail

coefficient_bp = Blueprint("coefficient", __name__)

TASKS: Dict[str, dict] = {}
TASKS_LOCK = threading.Lock()


def _to_native(obj):
    if isinstance(obj, dict):
        return {str(k): _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(x) for x in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d")
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _serialize_weather(weather_48: Optional[pd.DataFrame]):
    if weather_48 is None:
        return None
    records = weather_48.to_dict(orient="records")
    out = []
    for r in records:
        nr = {}
        for k, v in r.items():
            if v is None:
                nr[k] = None
                continue
            if hasattr(v, "strftime"):
                nr[k] = v.strftime("%Y-%m-%d %H:%M")
                continue
            try:
                fv = float(v)
                nr[k] = None if (fv != fv) else fv
            except (TypeError, ValueError):
                nr[k] = str(v)
        out.append(nr)
    return out


def _build_payload(result, target_date_str, window_days):
    correction = result.get("correction_log") or []
    base_coeffs = [float(c["base_coefficient"]) for c in correction]
    final_coeffs = [float(c) for c in result["coefficients"]]
    hours = [str(c.get("time_label", "")) for c in correction]

    # ===== 新增：所有策略 × 半衰期的修正前系数曲线 =====
    all_coeffs_curves = []
    try:
        all_df = result.get("all_coeffs")
        if all_df is not None and not all_df.empty:
            for (fam, hl), group in all_df.groupby(["strategy_family", "half_life"]):
                group = group.sort_values("point")
                data = [None] * 48
                for _, row in group.iterrows():
                    p = int(row["point"])
                    if 0 <= p < 48:
                        data[p] = float(row["coefficient"])
                all_coeffs_curves.append(
                    {
                        "name": f"{fam} · HL={hl}",
                        "strategy_family": str(fam),
                        "half_life": float(hl),
                        "data": data,
                    }
                )
    except Exception as e:
        print(f"[Coefficient] 构建多策略曲线失败: {e}")

    return {
        "success": True,
        "strategy": result.get("strategy"),
        "half_life": (
            float(result["half_life"]) if result.get("half_life") is not None else None
        ),
        "target_date": target_date_str,
        "window_days": window_days,
        "hours": hours,
        "base_coefficients": base_coeffs,
        "coefficients": final_coeffs,
        "all_coeffs_curves": all_coeffs_curves,  # ← 新增
        "correction_details": correction,
        "weather_data": _serialize_weather(result.get("weather_48")),
        "weather_meta": result.get("weather_meta"),
        "coeff_min": float(result.get("coeff_min_used", 0.1)),
        "coeff_max": float(result.get("coeff_max_used", 1.9)),
    }


def _run_task(
    task_id: str,
    history_df: pd.DataFrame,
    weather_df: Optional[pd.DataFrame],
    target_date: datetime,
    window_days: int,
    detection_offset: int,
    coeff_min: Optional[float],
    coeff_max: Optional[float],
    weather_overrides: Optional[Dict[str, any]] = None,
):
    def log_progress(stage, current, total, message=""):
        with TASKS_LOCK:
            if task_id in TASKS:
                TASKS[task_id]["progress"] = {
                    "stage": str(stage),
                    "current": int(current),
                    "total": int(total),
                    "message": str(message),
                }

    # 备份并应用天气配置覆盖
    backup = {}
    if weather_overrides:
        for k in WEATHER_CONFIG_KEYS:
            if hasattr(cfg_module, k):
                backup[k] = getattr(cfg_module, k)
        for k, v in weather_overrides.items():
            if k in WEATHER_CONFIG_KEYS:
                setattr(cfg_module, k, v)

    try:
        log_progress("初始化", 0, 1, "加载历史价差并训练模型…")
        predictor = CoefficientPredictor(history_df=history_df)

        result = predictor.predict(
            target_date,
            weather_df if weather_df is not None else pd.DataFrame(),
            window_days=window_days,
            detection_offset_days=detection_offset,
            progress_callback=log_progress,
            coeff_min=coeff_min,
            coeff_max=coeff_max,
        )

        payload = _to_native(
            _build_payload(result, target_date.strftime("%Y-%m-%d"), window_days)
        )

        with TASKS_LOCK:
            TASKS[task_id]["result"] = payload
            TASKS[task_id]["status"] = "done"
    except Exception as e:
        import traceback

        traceback.print_exc()
        with TASKS_LOCK:
            TASKS[task_id]["error"] = str(e)
            TASKS[task_id]["status"] = "error"
    finally:
        # 恢复默认
        for k, v in backup.items():
            setattr(cfg_module, k, v)


@coefficient_bp.post("/predict")
def predict():
    try:
        node_type = (request.form.get("nodeType") or "unified").strip()
        node_name = (request.form.get("nodeName") or "").strip()
        target_date_str = (request.form.get("targetDate") or "").strip()
        window_days = int(request.form.get("windowDays", 45))
        detection_offset = int(request.form.get("detectionOffset", 3))

        if not target_date_str:
            return fail("请选择预测日期")
        if window_days < 15 or window_days > 120:
            return fail("回看窗口需在 15~120 天之间")
        if node_type == "plant" and not node_name:
            return fail("请选择电厂节点")

        coeff_min_val = request.form.get("coeffMin")
        coeff_max_val = request.form.get("coeffMax")
        try:
            coeff_min = float(coeff_min_val) if coeff_min_val else None
            coeff_max = float(coeff_max_val) if coeff_max_val else None
        except Exception:
            coeff_min = coeff_max = None
        # 天气配置
        weather_config_json = request.form.get("weatherConfig") or "{}"
        try:
            weather_overrides = json.loads(weather_config_json)
            if not isinstance(weather_overrides, dict):
                weather_overrides = {}
        except Exception:
            weather_overrides = {}
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

        # 1) 构建历史价差
        history_df = build_gap_df(
            node_type=node_type,
            node_name=node_name or None,
            start_date=None,
            end_date=None,
        )

        # 2) 天气文件（可选）
        weather_df = None
        weather_file = request.files.get("weather_file")
        if weather_file and weather_file.filename:
            if not weather_file.filename.lower().endswith((".xlsx", ".xls")):
                return fail("天气文件仅支持 .xlsx / .xls")
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=os.path.splitext(weather_file.filename)[1],
                ) as tmp:
                    weather_file.save(tmp.name)
                    tmp_path = tmp.name

                weather_df = pd.read_excel(tmp_path)
                if "time" not in weather_df.columns:
                    weather_df = weather_df.rename(
                        columns={weather_df.columns[0]: "time"}
                    )
                weather_df["time"] = pd.to_datetime(weather_df["time"])
            except Exception as e:
                return fail(f"读取天气文件失败：{e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

        # 3) 创建任务
        task_id = str(uuid.uuid4())[:12]
        with TASKS_LOCK:
            TASKS[task_id] = {
                "status": "running",
                "progress": {
                    "stage": "排队中",
                    "current": 0,
                    "total": 1,
                    "message": "",
                },
                "result": None,
                "error": None,
            }

        t = threading.Thread(
            target=_run_task,
            args=(
                task_id,
                history_df,
                weather_df,
                target_date,
                window_days,
                detection_offset,
                coeff_min,
                coeff_max,
                weather_overrides,
            ),
            daemon=True,
        )
        t.start()

        return success({"taskId": task_id}, msg="任务已启动")
    except Exception as e:
        import traceback

        traceback.print_exc()
        return fail(f"启动失败：{e}")


@coefficient_bp.get("/progress/<task_id>")
def progress(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return fail("任务不存在", code=404), 404
        resp = {
            "status": task["status"],
            "progress": task["progress"],
        }
        if task["status"] == "done":
            resp["result"] = task["result"]
        elif task["status"] == "error":
            resp["error"] = task["error"]
        return success(resp)


@coefficient_bp.get("/weather-config")
def weather_config():
    """返回可配置的天气参数默认值（供前端弹窗初始化）"""
    defaults = {}
    for k in WEATHER_CONFIG_KEYS:
        if hasattr(cfg_module, k):
            defaults[k] = getattr(cfg_module, k)
    return success({"defaults": defaults})
