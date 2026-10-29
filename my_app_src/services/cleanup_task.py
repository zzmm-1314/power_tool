"""后台清理任务：数据库中已有数据的日期，自动删除对应的临时数据"""

import threading
from config import Config
from services.database_provider import fetch_from_database
from services.temp_manager import get_db_conn


class CleanupTask:
    def __init__(self, interval: int = None):
        self.interval = interval or getattr(Config, "TEMP_CLEAN_INTERVAL", 300)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="temp-cleanup", daemon=True
        )
        self._thread.start()
        print(f"[Cleanup] 临时数据清理任务已启动，间隔 {self.interval}s")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        if self._stop.wait(5):
            return
        while not self._stop.is_set():
            try:
                self.scan_once()
            except Exception as e:
                print(f"[Cleanup] 扫描异常: {e}")
            self._stop.wait(self.interval)

    def scan_once(self) -> int:
        removed = 0
        conn = get_db_conn()

        try:
            with conn.cursor() as cursor:
                # 获取所有临时数据
                cursor.execute(
                    "SELECT id, data_type, sub_type, node_name, date FROM temp_data"
                )
                rows = cursor.fetchall()

            for row in rows:
                data_type = row["data_type"]
                sub_type = row["sub_type"]
                date = row["date"]
                node_name = row["node_name"]

                # 业务判断：跳过只存在于临时库且逻辑不同步的数据类型
                if data_type in ("load", "pv", "day-ahead"):
                    pass  # 仍然执行清理判断

                try:
                    # 查询正式库是否有数据
                    df = fetch_from_database(
                        data_type, sub_type, date, node_name or None
                    )
                    if df is not None and not df.empty:
                        # 正式库已同步，从临时库删除
                        with conn.cursor() as del_cursor:
                            del_cursor.execute(
                                "DELETE FROM temp_data WHERE id=%s", (row["id"],)
                            )
                            removed += 1
                            print(
                                f"[Cleanup] 正式库已有 {data_type} - {date}，删除临时记录 ID={row['id']}"
                            )
                except Exception as e:
                    print(f"[Cleanup] 检查 ID={row['id']} 失败: {e}")

        finally:
            conn.close()

        return removed


_instance: CleanupTask | None = None


def get_cleanup_task() -> CleanupTask:
    global _instance
    if _instance is None:
        _instance = CleanupTask()
    return _instance
