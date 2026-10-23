"""后台清理任务：数据库中已有数据的日期，自动删除对应临时 Excel"""

import os
import threading

from config import Config
from services.database_provider import fetch_from_database
from services.temp_manager import TempManager


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
        # 启动后稍等片刻再首扫，避免抢占启动资源
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

        # ① 结构化临时文件
        for item in TempManager.list_all():
            if item["dataType"] in ("load", "pv", "day-ahead"):
                continue
            if item["dataType"] == "spread" and item["subType"] == "unified":
                continue
            try:
                df = fetch_from_database(
                    item["dataType"],
                    item["subType"],
                    item["date"],
                    item["nodeName"] or None,
                )
                if df is not None and not df.empty:
                    if TempManager.delete_by_relpath(item["path"]):
                        removed += 1
                        print(f"[Cleanup] 删除 {item['path']}")
            except Exception as e:
                print(f"[Cleanup] 检查 {item['path']} 失败: {e}")

        # ② 负荷原始文件
        removed += self._scan_load_files()

        # ③ 光伏原始文件（新增）
        removed += self._scan_pv_files()

        # ④ 日前电价统一结算点
        removed += self._scan_day_ahead_unified_files()
        # ⑤ 实时价格（新增）
        removed += self._scan_spread_unified_files()
        # ⑥ 价差分析 · 电厂节点实时文件
        removed += self._scan_spread_plant_files()
        return removed

    def _scan_pv_files(self) -> int:
        """扫描光伏文件（pv + load 目录），数据库已有则删除"""
        import os
        from services.load_parser import (
            parse_load_excel,
            detect_kind_from_filename,
            TARGET_DEVICE,
        )

        removed = 0

        dirs = [
            os.path.join(TempManager.base_dir(), "pv"),
            os.path.join(TempManager.base_dir(), "load"),  # 兼容旧文件
        ]

        for d in dirs:
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if not fn.lower().endswith((".xlsx", ".xls")):
                    continue

                raw_kind = detect_kind_from_filename(fn)
                if raw_kind not in ("pv", "pv_forecast"):
                    continue

                fp = os.path.join(d, fn)
                try:
                    items = parse_load_excel(fp, kind=raw_kind)
                except Exception as e:
                    print(f"[Cleanup] 解析光伏文件 {fn} 失败: {e}")
                    continue

                if not items:
                    continue

                all_in_db = True
                for it in items:
                    df = fetch_from_database("pv", "", it["date"], TARGET_DEVICE)
                    if df is None or df.empty:
                        all_in_db = False
                        break

                if all_in_db:
                    try:
                        TempManager.delete_by_relpath(relpath)
                        removed += 1
                        print(f"[Cleanup] 数据库已更新，删除光伏临时文件: {fn}")
                    except OSError as e:
                        print(f"[Cleanup] 删除 {fn} 失败: {e}")

        return removed

    def _scan_day_ahead_unified_files(self) -> int:
        import os
        from services.day_ahead_parser import (
            parse_unified_price_excel,
            TARGET_DEVICE_UNIFIED,
        )

        removed = 0
        d = os.path.join(TempManager.base_dir(), "day-ahead", "unified")
        if not os.path.isdir(d):
            return 0

        for fn in os.listdir(d):
            if not fn.lower().endswith((".xlsx", ".xls")):
                continue
            fp = os.path.join(d, fn)
            try:
                items = parse_unified_price_excel(fp)
            except Exception as e:
                print(f"[Cleanup] 解析 {fn} 失败: {e}")
                continue

            if not items:
                continue

            all_in_db = True
            for it in items:
                df = fetch_from_database(
                    "day-ahead", "unified", it["date"], TARGET_DEVICE_UNIFIED
                )
                if df is None or df.empty:
                    all_in_db = False
                    break

            if all_in_db:
                try:
                    TempManager.delete_by_relpath(relpath)
                    removed += 1
                    print(f"[Cleanup] 数据库已更新，删除日前电价临时文件: {fn}")
                except OSError as e:
                    print(f"[Cleanup] 删除 {fn} 失败: {e}")

        return removed

    def _scan_load_files(self) -> int:
        from services.load_parser import parse_load_excel, TARGET_DEVICE
        import os

        removed = 0
        load_dir = os.path.join(TempManager.base_dir(), "load")
        if not os.path.isdir(load_dir):
            return 0

        for fn in os.listdir(load_dir):
            if not fn.lower().endswith((".xlsx", ".xls")):
                continue
            fp = os.path.join(load_dir, fn)
            try:
                items = parse_load_excel(fp)  # 默认只保留浙江电网
            except Exception as e:
                print(f"[Cleanup] 解析负荷文件 {fn} 失败: {e}")
                continue

            if not items:
                continue

            all_in_db = True
            for it in items:
                df = fetch_from_database("load", "", it["date"], TARGET_DEVICE)
                if df is None or df.empty:
                    all_in_db = False
                    break

            if all_in_db:
                try:
                    TempManager.delete_by_relpath(relpath)
                    removed += 1
                    print(f"[Cleanup] 数据库已更新，删除负荷临时文件: {fn}")
                except OSError as e:
                    print(f"[Cleanup] 删除 {fn} 失败: {e}")

        return removed

    def _scan_day_ahead_plant_files(self) -> int:
        """
        扫描 temp/day-ahead/plant/*.xlsx
        对每个文件的每一列日期，若数据库已有该节点数据 → 从文件中移除该列
        若文件无剩余列 → 删除整个文件
        """
        import os
        import pandas as pd
        from services.day_ahead_parser import extract_date_from_text

        root = os.path.join(TempManager.base_dir(), "day-ahead", "plant")
        if not os.path.isdir(root):
            return 0

        removed_cols = 0

        for fn in os.listdir(root):
            if not fn.lower().endswith((".xlsx", ".xls")):
                continue
            path = os.path.join(root, fn)
            node_name = os.path.splitext(fn)[0]

            try:
                df = pd.read_excel(path, index_col=0, dtype=object)
            except Exception as e:
                print(f"[Cleanup] 读取 {fn} 失败: {e}")
                continue

            if df.empty or len(df.columns) == 0:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue

            keep_cols = []
            for col in df.columns:
                date_str = extract_date_from_text(str(col)) or str(col).strip()
                df_db = fetch_from_database("day-ahead", "plant", date_str, node_name)
                if df_db is not None and not df_db.empty:
                    removed_cols += 1
                    print(
                        f"[Cleanup] {node_name} 的 {date_str} 已入库，"
                        f"从临时文件移除"
                    )
                else:
                    keep_cols.append(col)

            if not keep_cols:
                try:
                    os.remove(path)
                    print(f"[Cleanup] 已删除节点临时文件: {fn}")
                except OSError as e:
                    print(f"[Cleanup] 删除 {fn} 失败: {e}")
            elif len(keep_cols) < len(df.columns):
                try:
                    df[keep_cols].to_excel(path)
                except Exception as e:
                    print(f"[Cleanup] 重写 {fn} 失败: {e}")

        return removed_cols

    def _scan_spread_unified_files(self) -> int:
        """扫描 temp/spread/unified/ 下的实时价格文件"""
        import os
        from services.day_ahead_parser import (
            TARGET_DEVICE_REAL_TIME,
            parse_real_time_price_excel,
        )

        removed = 0
        d = os.path.join(TempManager.base_dir(), "spread", "unified")
        if not os.path.isdir(d):
            return 0

        for fn in os.listdir(d):
            if not fn.lower().endswith((".xlsx", ".xls")):
                continue
            fp = os.path.join(d, fn)
            try:
                items = parse_real_time_price_excel(fp)
            except Exception:
                continue
            if not items:
                continue

            all_in_db = True
            for it in items:
                df = fetch_from_database(
                    "spread", "unified", it["date"], TARGET_DEVICE_REAL_TIME
                )
                if df is None or df.empty:
                    all_in_db = False
                    break

            if all_in_db:
                try:
                    TempManager.delete_by_relpath(relpath)
                    removed += 1
                except OSError:
                    pass

        return removed

    def _scan_spread_plant_files(self) -> int:
        """扫描 temp/spread/plant/*.xlsx 逐列清理"""
        import os
        import pandas as pd
        from services.day_ahead_parser import extract_date_from_text

        root = os.path.join(TempManager.base_dir(), "spread", "plant")
        if not os.path.isdir(root):
            return 0

        removed_cols = 0

        for fn in os.listdir(root):
            if not fn.lower().endswith((".xlsx", ".xls")):
                continue
            path = os.path.join(root, fn)
            node_name = os.path.splitext(fn)[0]

            try:
                df = pd.read_excel(path, index_col=0, dtype=object)
            except Exception as e:
                print(f"[Cleanup] 读取 {fn} 失败: {e}")
                continue

            if df.empty or len(df.columns) == 0:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue

            keep_cols = []
            for col in df.columns:
                date_str = extract_date_from_text(str(col)) or str(col).strip()
                df_db = fetch_from_database("spread", "plant", date_str, node_name)
                if df_db is not None and not df_db.empty:
                    removed_cols += 1
                    print(
                        f"[Cleanup] {node_name} 实时 {date_str} 已入库，"
                        f"从临时文件移除"
                    )
                else:
                    keep_cols.append(col)

            if not keep_cols:
                try:
                    os.remove(path)
                    print(f"[Cleanup] 已删除实时节点临时文件: {fn}")
                except OSError as e:
                    print(f"[Cleanup] 删除 {fn} 失败: {e}")
            elif len(keep_cols) < len(df.columns):
                try:
                    df[keep_cols].to_excel(path)
                except Exception as e:
                    print(f"[Cleanup] 重写 {fn} 失败: {e}")

        return removed_cols


# ---------- 单例 ----------
_instance: CleanupTask | None = None


def get_cleanup_task() -> CleanupTask:
    global _instance
    if _instance is None:
        _instance = CleanupTask()
    return _instance
