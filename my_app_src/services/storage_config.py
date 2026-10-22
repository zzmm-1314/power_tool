"""存储目录配置：支持运行时切换临时数据根目录，并可选迁移文件"""

import json
import os
import shutil
from typing import Optional, Tuple

from config import Config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "data", "storage_config.json")


def _ensure_dir(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        return os.access(path, os.W_OK)
    except Exception:
        return False


class StorageConfig:
    _cache: Optional[dict] = None

    # ---------- 读写配置文件 ----------

    @classmethod
    def _load(cls) -> dict:
        if cls._cache is not None:
            return cls._cache
        if not os.path.exists(CONFIG_FILE):
            cls._cache = {"temp_data_dir": Config.TEMP_DATA_DIR}
            return cls._cache
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "temp_data_dir" not in data:
                data["temp_data_dir"] = Config.TEMP_DATA_DIR
            cls._cache = data
            return data
        except Exception:
            cls._cache = {"temp_data_dir": Config.TEMP_DATA_DIR}
            return cls._cache

    @classmethod
    def _save(cls, data: dict) -> None:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        cls._cache = data

    # ---------- 对外接口 ----------

    @classmethod
    def get_temp_dir(cls) -> str:
        """获取当前生效的临时数据根目录"""
        data = cls._load()
        path = data.get("temp_data_dir") or Config.TEMP_DATA_DIR
        _ensure_dir(path)
        return path

    @classmethod
    def set_temp_dir(cls, new_path: str, migrate: bool = False) -> dict:
        """
        切换临时数据根目录
        - new_path: 新目录绝对路径（前端传服务器路径）
        - migrate: True 时把旧目录所有文件复制到新目录
        """
        new_path = (new_path or "").strip()
        if not new_path:
            return {"ok": False, "error": "路径不能为空"}

        new_path = os.path.abspath(new_path)
        if not _ensure_dir(new_path):
            return {"ok": False, "error": f"目录不存在或不可写：{new_path}"}

        old_path = cls.get_temp_dir()
        migrated, skipped = 0, 0

        if migrate and os.path.abspath(old_path) != new_path:
            migrated, skipped = cls._migrate(old_path, new_path)

        data = cls._load()
        data["temp_data_dir"] = new_path
        cls._save(data)

        return {
            "ok": True,
            "oldPath": old_path,
            "newPath": new_path,
            "migrated": migrated,
            "skipped": skipped,
        }

    # ---------- 文件迁移（仅复制，不动旧目录） ----------

    @classmethod
    def _migrate(cls, old_dir: str, new_dir: str) -> Tuple[int, int]:
        migrated, skipped = 0, 0
        if not os.path.isdir(old_dir):
            return migrated, skipped

        for root, _dirs, files in os.walk(old_dir):
            rel = os.path.relpath(root, old_dir)
            target_root = new_dir if rel == "." else os.path.join(new_dir, rel)
            os.makedirs(target_root, exist_ok=True)

            for fn in files:
                src = os.path.join(root, fn)
                dst = os.path.join(target_root, fn)
                if os.path.exists(dst):
                    skipped += 1
                    continue
                try:
                    shutil.copy2(src, dst)
                    migrated += 1
                except Exception as e:
                    print(f"[StorageConfig] 迁移失败 {src} → {dst}: {e}")
                    skipped += 1

        return migrated, skipped
