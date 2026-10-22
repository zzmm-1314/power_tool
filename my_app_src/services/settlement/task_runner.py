"""任务调度（原 tasks.py，改进线程安全）"""

import threading
import uuid
from datetime import datetime
from typing import Dict, Optional

from services.settlement.actual import fill_data
from services.settlement.sim_v1 import fill_simulation_data
from services.settlement.sim_v2 import fill_simulation_data_v2

tasks: Dict[str, dict] = {}
_tasks_lock = threading.Lock()


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

        elif task_type == "jiaojiang":
            fill_simulation_data(
                detail_folder=params["folder"],
                fixed_power_file=params["fixed_file"],
                strategy_file=params["strategy_file"],
                stat_file=params["stat_file"],
                info_file=params["info_file"],
                target_file=params["target_file"],
                annual_price=float(params["annual_price"]),
                tenday_prices=[
                    float(params["tenday_early"]),
                    float(params["tenday_mid"]),
                    float(params["tenday_late"]),
                ],
                selected_dates=params.get("selected_dates") or [],
                log_func=log_func,
                progress_func=progress_func,
            )

        elif task_type == "xiandai":
            fill_simulation_data_v2(
                spot_file=params["spot_file"],
                stat_file=params["stat_file"],
                strategy_file=params["strategy_file"],
                info_spot_file=params["info_spot_file"],
                info_contract_file=params["info_contract_file"],
                target_file=params["target_file"],
                annual_price=float(params["annual_price"]),
                monthly_price=float(params["monthly_price"]),
                tenday_prices=[
                    float(params["tenday_early"]),
                    float(params["tenday_mid"]),
                    float(params["tenday_late"]),
                ],
                selected_dates=params.get("selected_dates") or [],
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
                tasks[task_id]["progress"]["percent"] = 100
                tasks[task_id]["finishedAt"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
