"""临时 Excel 数据管理：保存、读取、列表、删除"""

import os
import re
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from services.local_paths import get_local_mirror_dir
from services.storage_config import StorageConfig
import pandas as pd

from config import Config

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]+')


def _safe(name: str) -> str:
    """把名字安全化为路径片段（仅替换危险字符，保留中文/空格/常见符号）"""
    if not name:
        return ""
    cleaned = _INVALID_CHARS.sub("_", str(name).strip())
    return cleaned.strip("._") or "unnamed"


class TempManager:
    """临时 Excel 文件统一管理"""

    @staticmethod
    def base_dir() -> str:
        """业务读取根目录：本地镜像"""
        d = str(get_local_mirror_dir())
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def write_dir() -> str:
        """业务写入根目录：云盘（真相源）"""
        d = StorageConfig.get_temp_dir()
        os.makedirs(d, exist_ok=True)
        return d

    # ==================== 镜像 ====================

    @staticmethod
    def mirror_to_local(cloud_path: str) -> None:
        """把云盘上的某个文件立即镜像到本地，保证上传后可读"""
        cloud_root = TempManager.write_dir()
        local_root = TempManager.base_dir()
        try:
            rel = os.path.relpath(cloud_path, cloud_root)
            if rel.startswith(".."):
                return
            dst = os.path.join(local_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(cloud_path, dst)
        except Exception as e:
            print(f"[Temp] 镜像失败 {cloud_path}: {e}")

    @staticmethod
    def mirror_path_to_local(relpath: str) -> None:
        cloud_path = os.path.join(TempManager.write_dir(), relpath)
        if os.path.exists(cloud_path):
            TempManager.mirror_to_local(cloud_path)

    # ==================== 路径解析（写入用，基于云盘） ====================

    @staticmethod
    def resolve_path(
        data_type: str,
        sub_type: str,
        date: str,
        node_name: Optional[str] = None,
    ) -> str:
        parts = [TempManager.write_dir(), _safe(data_type)]
        if sub_type:
            parts.append(_safe(sub_type))
        if node_name:
            parts.append(_safe(node_name))
        parts.append(f"{_safe(date)}.xlsx")
        return os.path.join(*parts)

    # ==================== 保存（写云盘 + 立即镜像） ====================

    @staticmethod
    def save(
        file_storage,
        data_type: str,
        sub_type: str,
        date: str,
        node_name: Optional[str] = None,
    ) -> str:
        path = TempManager.resolve_path(data_type, sub_type, date, node_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            os.remove(path)
        file_storage.save(path)
        TempManager.mirror_to_local(path)
        return path

    @staticmethod
    def save_raw(file_storage, data_type: str, sub_type: str = "") -> str:
        parts = [TempManager.write_dir(), _safe(data_type)]
        if sub_type:
            for seg in sub_type.split("/"):
                seg = seg.strip()
                if seg:
                    parts.append(_safe(seg))

        base = os.path.join(*parts)
        os.makedirs(base, exist_ok=True)

        raw_name = os.path.basename(file_storage.filename or "upload.xlsx")
        ext = os.path.splitext(raw_name)[1].lower()
        if ext not in (".xlsx", ".xls"):
            raw_name += ".xlsx"

        path = os.path.join(base, raw_name)
        if os.path.exists(path):
            os.remove(path)

        file_storage.save(path)
        TempManager.mirror_to_local(path)
        return path

    # ==================== 读取（本地优先，缺失时回退云盘） ====================

    @staticmethod
    def load(
        data_type: str,
        sub_type: str,
        date: str,
        node_name: Optional[str] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        # 先在本地镜像里找
        rel_parts = [_safe(data_type)]
        if sub_type:
            rel_parts.append(_safe(sub_type))
        if node_name:
            rel_parts.append(_safe(node_name))
        rel_parts.append(f"{_safe(date)}.xlsx")
        rel = "/".join(rel_parts)

        local_path = os.path.join(TempManager.base_dir(), rel.replace("/", os.sep))
        cloud_path = os.path.join(TempManager.write_dir(), rel.replace("/", os.sep))

        path = local_path if os.path.exists(local_path) else None
        if path is None and os.path.exists(cloud_path):
            # 本地缺失 → 从云盘补
            TempManager.mirror_to_local(cloud_path)
            path = local_path if os.path.exists(local_path) else cloud_path

        if path is None:
            return None, None
        try:
            return pd.read_excel(path), path
        except Exception as e:
            print(f"[Temp] 读取失败 {path}: {e}")
            return None, path

    # ==================== 列表（扫本地镜像） ====================

    @staticmethod
    def list_all() -> List[Dict]:
        base = TempManager.base_dir()
        items: List[Dict] = []

        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.lower().endswith((".xlsx", ".xls")):
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, base).replace("\\", "/")
                parts = rel.split("/")
                data_type = parts[0] if parts else ""
                sub_type = parts[1] if len(parts) >= 3 else ""
                node_name = parts[2] if len(parts) >= 4 else ""
                date = os.path.splitext(parts[-1])[0]
                stat = os.stat(full)
                items.append(
                    {
                        "path": rel,
                        "dataType": data_type,
                        "subType": sub_type,
                        "nodeName": node_name,
                        "date": date,
                        "fileName": fn,
                        "size": stat.st_size,
                        "uploadedAt": datetime.fromtimestamp(stat.st_mtime).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )
        items.sort(key=lambda x: x["uploadedAt"], reverse=True)
        return items

    # ==================== 删除（本地 + 云盘） ====================

    @staticmethod
    def delete_by_relpath(relpath: str) -> bool:
        ok = False
        for root in (TempManager.base_dir(), TempManager.write_dir()):
            full = os.path.abspath(os.path.join(root, relpath))
            if not full.startswith(os.path.abspath(root) + os.sep):
                continue
            if os.path.exists(full):
                try:
                    os.remove(full)
                    ok = True
                except OSError as e:
                    print(f"[Temp] 删除失败 {full}: {e}")
            # 清理空目录
            parent = os.path.dirname(full)
            while os.path.abspath(parent) != os.path.abspath(root):
                try:
                    if not os.listdir(parent):
                        os.rmdir(parent)
                        parent = os.path.dirname(parent)
                    else:
                        break
                except OSError:
                    break
        return ok

    # ---------- 原样保存（用于负荷文件，保留原始文件名） ----------

    @staticmethod
    def save_raw(file_storage, data_type: str, sub_type: str = "") -> str:
        """原样保存文件（负荷/光伏/日前电价等保留原名）
        - sub_type 支持多级路径，如 "plant/万华热电"
        - 每一段单独 _safe，避免 / 被误替换
        """
        parts = [TempManager.base_dir(), _safe(data_type)]
        if sub_type:
            for seg in sub_type.split("/"):
                seg = seg.strip()
                if seg:
                    parts.append(_safe(seg))

        base = os.path.join(*parts)
        os.makedirs(base, exist_ok=True)

        raw_name = os.path.basename(file_storage.filename or "upload.xlsx")
        ext = os.path.splitext(raw_name)[1].lower()
        if ext not in (".xlsx", ".xls"):
            raw_name += ".xlsx"

        path = os.path.join(base, raw_name)
        if os.path.exists(path):
            os.remove(path)

        file_storage.save(path)
        return path

    # ---------- 批量新增 ----------

    @classmethod
    def add_batch(cls, names: List[str], description: str = "") -> dict:
        """批量新增节点
        返回 {added: [...], skipped: [{name, reason}, ...]}
        """
        if not isinstance(names, list):
            return {"ok": False, "error": "names 必须是列表"}

        with _lock:
            data = cls._load()
            existing = {n.get("name") for n in data if n.get("name")}
            new_id = max([n.get("id", 0) for n in data], default=0) + 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            added: List[dict] = []
            skipped: List[dict] = []

            for raw in names:
                name = (raw or "").strip()
                if not name:
                    continue

                err = _validate_name(name)
                if err:
                    skipped.append({"name": name, "reason": err})
                    continue
                if name in existing:
                    skipped.append({"name": name, "reason": "已存在"})
                    continue

                node = {
                    "id": new_id,
                    "name": name,
                    "description": (description or "").strip(),
                    "createdAt": now,
                    "updatedAt": now,
                }
                data.append(node)
                existing.add(name)
                added.append(node)
                new_id += 1

            if added:
                cls._save(data)

        return {"ok": True, "added": added, "skipped": skipped}

    # ---------- 批量删除 ----------

    @classmethod
    def delete_batch(cls, ids: List[int], purge: bool = True) -> dict:
        if not isinstance(ids, list) or not ids:
            return {"ok": False, "error": "请提供要删除的节点 ID"}

        with _lock:
            data = cls._load()
            id_set = {int(i) for i in ids}
            targets = [n for n in data if n.get("id") in id_set]
            rest = [n for n in data if n.get("id") not in id_set]

            if not targets:
                return {"ok": False, "error": "未找到匹配的节点"}

            cls._save(rest)

            if purge:
                for t in targets:
                    _purge_node_excel(t["name"])

        return {"ok": True, "deleted": targets, "count": len(targets)}
