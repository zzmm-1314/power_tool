"""任务调度（原 tasks.py，改进线程安全）"""

import threading
import uuid
from datetime import datetime
from typing import Dict, Optional

from services.settlement.actual import fill_data
from services.settlement.sim_v2 import fill_simulation_data_v2

tasks: Dict[str, dict] = {}
_tasks_lock = threading.Lock()


def _as_bool(value) -> bool:
    """前端开关值转布尔：兼容 true/"true"/1/"on" 等写法，缺省为 False"""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def start_task(task_type: str, params: dict) -> str:
    """创建并启动新任务，返回 task_id"""
    task_id = str(uuid.uuid4())
    with _tasks_lock:
        tasks[task_id] = {
            "task_id": task_id,
            "type": task_type,
            "status": "running",
            "logs": [],
            "finished": False,
            "progress": {"current": 0, "total": 0, "percent": 0},
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finishedAt": None,
        }
    t = threading.Thread(
        target=run_task, args=(task_id, task_type, params), daemon=True
    )
    t.start()
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    with _tasks_lock:
        task = tasks.get(task_id)
        return dict(task) if task else None


def run_task(task_id: str, task_type: str, params: dict):
    def log_func(msg):
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]["logs"].append(str(msg))

    def progress_func(current, total):
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]["progress"] = {
                    "current": current,
                    "total": total,
                    "percent": round(current / total * 100, 1) if total > 0 else 0,
                }

    try:
        if task_type == "actual":
            fill_data(
                folder_path=params["folder"],
                target_file=params["target_file"],
                selected_dates=params.get("selected_dates") or [],
                log_func=log_func,
                progress_func=progress_func,
            )

        elif task_type == "general":
            fill_simulation_data_v2(
                spot_data=params["spot_data"],
                stat_data=params["stat_data"],
                strategy_month_data=params["strategy_month_data"],
                strategy_tenday_data=params["strategy_tenday_data"],
                info_spot_day_data=params["info_spot_day_data"],
                info_spot_rt_data=params["info_spot_rt_data"],
                info_contract_data=params["info_contract_data"],
                target_file=params["target_file"],
                annual_price=float(params["annual_price"]),
                monthly_price=float(params["monthly_price"]),
                tenday_prices=[
                    float(params["tenday_early"]),
                    float(params["tenday_mid"]),
                    float(params["tenday_late"]),
                ],
                selected_dates=params.get("selected_dates") or [],
                declaration_file=params.get("declaration_file") or None,
                node_name=params.get("node_name") or params.get("nodeName"),
                enable_rolling_spot=_as_bool(
                    params.get("enable_rolling_spot", params.get("enableRollingSpot"))
                ),
                enable_cross_province=_as_bool(
                    params.get("enable_cross_province", params.get("enableCrossProvince"))
                ),
                log_func=log_func,
                progress_func=progress_func,
            )
        else:
            raise ValueError(f"未知任务类型: {task_type}")

        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]["status"] = "completed"
    except Exception as e:
        log_func(f"发生异常: {e}")
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]["status"] = "error"
    finally:
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]["finished"] = True
                if tasks[task_id]["status"] == "completed":
                    tasks[task_id]["progress"]["percent"] = 100
                tasks[task_id]["finishedAt"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
