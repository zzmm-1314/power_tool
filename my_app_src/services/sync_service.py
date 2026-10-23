"""WPS 云盘目录 → 本地镜像的实时同步"""

import os
import shutil
import threading
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from services.local_paths import get_local_mirror_dir
from services.storage_config import StorageConfig


class _SyncHandler(FileSystemEventHandler):
    def __init__(self, source: Path, target: Path):
        self.source = source
        self.target = target

    def _rel(self, path: str) -> Optional[Path]:
        try:
            return Path(path).resolve().relative_to(self.source.resolve())
        except (ValueError, OSError):
            return None

    def _sync_file(self, src_path: str):
        rel = self._rel(src_path)
        if rel is None or not os.path.exists(src_path):
            return
        dst = self.target / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst)
            print(f"[sync] + {rel}", flush=True)
        except Exception as e:
            print(f"[sync] 复制失败 {rel}: {e}", flush=True)

    def _remove_file(self, src_path: str):
        rel = self._rel(src_path)
        if rel is None:
            return
        dst = self.target / rel
        try:
            if dst.exists():
                dst.unlink()
                print(f"[sync] - {rel}", flush=True)
        except Exception as e:
            print(f"[sync] 删除失败 {rel}: {e}", flush=True)

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            self._remove_file(event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            self._remove_file(event.src_path)
            self._sync_file(event.dest_path)


class SyncService:
    def __init__(self):
        self._observer: Optional[Observer] = None
        self._lock = threading.Lock()

    # ---------------- 全量同步 ----------------

    def full_sync(self) -> int:
        source = Path(StorageConfig.get_temp_dir()).resolve()
        target = get_local_mirror_dir().resolve()

        if source == target:
            print("[sync] 源与目标相同，跳过", flush=True)
            return 0
        if not source.is_dir():
            print(f"[sync] 源目录不可达：{source}", flush=True)
            return 0

        count = 0
        for root, _dirs, files in os.walk(source):
            for fn in files:
                if fn.startswith("~$"):
                    continue
                src = Path(root) / fn
                rel = src.relative_to(source)
                dst = target / rel
                try:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists() or os.path.getmtime(src) > os.path.getmtime(
                        dst
                    ):
                        shutil.copy2(src, dst)
                        count += 1
                except Exception as e:
                    print(f"[sync] 全量同步失败 {rel}: {e}", flush=True)
        print(f"[sync] 全量同步完成，更新 {count} 个文件", flush=True)
        return count

    # ---------------- 启动 / 重启 / 停止 ----------------

    def start(self):
        with self._lock:
            self._stop_locked()

            source = Path(StorageConfig.get_temp_dir()).resolve()
            target = get_local_mirror_dir().resolve()

            if source == target:
                print("[sync] 源与目标相同，不启动", flush=True)
                return
            if not source.is_dir():
                print(f"[sync] 源目录不可达，不启动：{source}", flush=True)
                return

            self.full_sync()

            handler = _SyncHandler(source, target)
            observer = Observer()
            observer.schedule(handler, str(source), recursive=True)
            observer.start()
            self._observer = observer
            print(f"[sync] 监控已启动：{source} → {target}", flush=True)

    def restart(self):
        self.start()

    def _stop_locked(self):
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
            self._observer = None

    def stop(self):
        with self._lock:
            self._stop_locked()


_instance: Optional[SyncService] = None


def get_sync_service() -> SyncService:
    global _instance
    if _instance is None:
        _instance = SyncService()
    return _instance
