import os
import json
import threading
import time
from datetime import datetime, timedelta
from config import Config
from services.db_store import get_db_conn
from utils.logger import get_logger

logger = get_logger("services.db_maintenance")

# 状态文件，用于记录最后一次执行清理的日期（防止同一天重启重复清理）
_STATE_FILE = os.path.join(Config.DATA_DIR, "maintenance_state.json")


def _get_last_cleanup_date() -> str:
    if not os.path.exists(_STATE_FILE):
        return ""
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("last_cleanup", "")
    except Exception:
        return ""


def _set_last_cleanup_date(date_str: str):
    try:
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_cleanup": date_str}, f)
    except Exception as e:
        logger.error(f"[Maintenance] 写入清理状态失败: {e}")


def _get_last_month_str() -> str:
    """获取上个月的 'YYYY-MM' 字符串"""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_month_day = first_day_this_month - timedelta(days=1)
    return last_month_day.strftime("%Y-%m")


def run_cleanup():
    """执行历史数据清理：保留当前月和上个月，删除更早的数据"""
    today = datetime.now()
    first_day_this_month = today.replace(day=1)

    # 计算保留边界：上个月的 1 号
    # 例如：今天是 3 月 20 号，first_day_this_month = 3月1日
    # first_day_this_month - timedelta(days=1) = 2月28日（或29日）
    # .replace(day=1) = 2月1日
    boundary_date = (first_day_this_month - timedelta(days=1)).replace(day=1)
    boundary_str = boundary_date.strftime("%Y-%m-%d")

    logger.info(f"[Maintenance] 开始清理早于 {boundary_str} 的合约及滚撮数据...")

    tables_to_clean = [
        ("tmp_contract", "`date`"),
        ("tmp_rolling_spot", "`trade_date`"),
        ("tmp_cross_province_spot", "`trade_date`"),
        ("tmp_settlement_actual", "`date`"),
    ]

    try:
        conn = get_db_conn()
        with conn.cursor() as cursor:
            for table, date_col in tables_to_clean:
                # 直接把边界之前的数据全部删除
                sql = f"DELETE FROM {table} WHERE {date_col} < %s"
                cursor.execute(sql, (boundary_str,))
                logger.info(
                    f"[Maintenance] 表 {table} 清理完成，删除了 {cursor.rowcount} 条记录。"
                )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"[Maintenance] 清理数据失败: {e}")
        return False


def _maintenance_worker():
    """后台守护线程的执行体"""
    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")

            # 判断：每月 20 号执行
            if now.day == 20:
                last_cleanup = _get_last_cleanup_date()
                if last_cleanup != today_str:
                    # 避免重启死循环，只有不是今天清理过才执行
                    success = run_cleanup()
                    if success:
                        _set_last_cleanup_date(today_str)
                        logger.info(f"[Maintenance] {today_str} 清理任务执行成功。")
        except Exception as e:
            logger.error(f"[Maintenance] 守护线程异常: {e}")

        # 每小时检查一次（3600秒）
        time.sleep(3600)


def start_maintenance_scheduler():
    """启动清理守护线程（由 app.py 调用）"""
    t = threading.Thread(target=_maintenance_worker, daemon=True, name="DbMaintenance")
    t.start()
    logger.info("[Maintenance] 合约数据自动清理守护线程已启动（每月20号执行）。")
