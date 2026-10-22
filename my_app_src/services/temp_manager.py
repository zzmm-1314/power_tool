"""临时 Excel 数据管理：保存、读取、列表、删除"""

import os
import re
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Tuple
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
        d = StorageConfig.get_temp_dir()
        os.makedirs(d, exist_ok=True)
        return d

    # ---------- 路径解析 ----------

    @staticmethod
    def resolve_path(
        data_type: str,
        sub_type: str,
        date: str,
        node_name: Optional[str] = None,
    ) -> str:
        parts = [TempManager.base_dir(), _safe(data_type)]
        if sub_type:
            parts.append(_safe(sub_type))
        if node_name:
            parts.append(_safe(node_name))
        parts.append(f"{_safe(date)}.xlsx")
        return os.path.join(*parts)

    # ---------- 保存 ----------

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

        # 同名文件覆盖（视为更新）
        if os.path.exists(path):
            os.remove(path)

        file_storage.save(path)
        return path

    # ---------- 读取 ----------

    @staticmethod
    def load(
        data_type: str,
        sub_type: str,
        date: str,
        node_name: Optional[str] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        path = TempManager.resolve_path(data_type, sub_type, date, node_name)
        if not os.path.exists(path):
            return None, None
        try:
            df = pd.read_excel(path)
            return df, path
        except Exception as e:
            print(f"[Temp] 读取 Excel 失败: {path} → {e}")
            return None, path

    # ---------- 列表 ----------

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

                data_type = ""
                sub_type = ""
                node_name = ""
                date = ""

                if len(parts) == 2:
                    # dataType/file.xlsx
                    data_type = parts[0]
                    date = os.path.splitext(parts[-1])[0]

                elif len(parts) == 3:
                    # dataType/subType/file.xlsx
                    data_type, sub_type = parts[0], parts[1]
                    if data_type == "day-ahead" and sub_type == "plant":
                        # 节点专属文件：文件名即节点名，无日期
                        node_name = os.path.splitext(parts[-1])[0]
                        date = ""
                    else:
                        date = os.path.splitext(parts[-1])[0]

                elif len(parts) == 4:
                    # dataType/subType/nodeName/file.xlsx
                    data_type = parts[0]
                    sub_type = parts[1]
                    node_name = parts[2]
                    date = os.path.splitext(parts[-1])[0]

                else:
                    continue

                # 文件名带日期的类型：从文件名解析
                if data_type in ("load", "pv") or (
                    data_type in ("day-ahead", "spread") and sub_type == "unified"
                ):
                    from services.load_parser import extract_date_from_filename

                    file_date = extract_date_from_filename(parts[-1])
                    if file_date:
                        date = file_date

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

    # ---------- 删除 ----------

    @staticmethod
    def delete_by_relpath(relpath: str) -> bool:
        base = TempManager.base_dir()
        full = os.path.abspath(os.path.join(base, relpath))
        # 防目录穿越
        if not full.startswith(os.path.abspath(base) + os.sep):
            return False
        if not os.path.exists(full):
            return False

        os.remove(full)

        # 递归清理空目录
        parent = os.path.dirname(full)
        while os.path.abspath(parent) != os.path.abspath(base):
            try:
                if not os.listdir(parent):
                    os.rmdir(parent)
                    parent = os.path.dirname(parent)
                else:
                    break
            except OSError:
                break
        return True

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
