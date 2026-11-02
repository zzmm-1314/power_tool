"""节点列表管理：新增 / 修改 / 删除 / 查询
节点清单存放于 data/plant_nodes.json（正式业务数据，不属于临时存储）。
节点的价格数据存在业务数据库中，改名 / 删除时同步更新数据库。
"""

import json
import os
import re
import threading
from datetime import datetime
from typing import List, Optional

from config import Config
from services.db_store import delete_node_data, rename_node

NODE_FILENAME = "plant_nodes.json"

_OLD_NODE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "temp",
    NODE_FILENAME,
)

_INVALID = re.compile(r'[\\/:*?"<>|]')
_lock = threading.Lock()


def _node_file() -> str:
    return os.path.join(Config.DATA_DIR, NODE_FILENAME)


def _validate_name(name: str) -> Optional[str]:
    name = (name or "").strip()
    if not name:
        return "节点名不能为空"
    if len(name) > 64:
        return "节点名不能超过 64 字符"
    if _INVALID.search(name):
        return '节点名不能包含 \\ / : * ? " < > | 字符'
    return None


class NodeManager:
    # ---------- 读写 ----------

    @classmethod
    def _load(cls) -> List[dict]:
        path = _node_file()

        # 首次访问：若新位置不存在、旧位置存在 → 自动复制
        if not os.path.exists(path) and os.path.exists(_OLD_NODE_FILE):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(_OLD_NODE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[NodeManager] 节点列表已迁移：" f"{_OLD_NODE_FILE} → {path}")
            except Exception as e:
                print(f"[NodeManager] 迁移节点列表失败：{e}")

        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @classmethod
    def _save(cls, data: List[dict]) -> None:
        path = _node_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 查询 ----------
    # ⚠ 不再自动扫描目录，完全以 JSON 中的录入节点为准

    @classmethod
    def list_all(cls) -> List[dict]:
        data = cls._load()
        data.sort(key=lambda n: n.get("name", ""))
        return data

    @classmethod
    def names(cls) -> List[str]:
        return [n["name"] for n in cls.list_all() if n.get("name")]

    @classmethod
    def find(cls, node_id: int) -> Optional[dict]:
        for n in cls._load():
            if n.get("id") == node_id:
                return n
        return None

    @classmethod
    def find_by_name(cls, name: str) -> Optional[dict]:
        for n in cls._load():
            if n.get("name") == name:
                return n
        return None

    # ---------- 新增 ----------

    @classmethod
    def add(cls, name: str, description: str = "") -> dict:
        name = (name or "").strip()
        err = _validate_name(name)
        if err:
            return {"ok": False, "error": err}

        with _lock:
            data = cls._load()
            if any(n.get("name") == name for n in data):
                return {"ok": False, "error": "节点名已存在"}

            new_id = max([n.get("id", 0) for n in data], default=0) + 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            node = {
                "id": new_id,
                "name": name,
                "description": (description or "").strip(),
                "createdAt": now,
                "updatedAt": now,
            }
            data.append(node)
            cls._save(data)
        return {"ok": True, "node": node}

    # ---------- 修改 ----------

    @classmethod
    def update(cls, node_id: int, name: str, description: str = "") -> dict:
        name = (name or "").strip()
        err = _validate_name(name)
        if err:
            return {"ok": False, "error": err}

        with _lock:
            data = cls._load()
            target = None
            for n in data:
                if n.get("id") == node_id:
                    target = n
                    break
            if not target:
                return {"ok": False, "error": "节点不存在"}
            if any(n.get("name") == name and n.get("id") != node_id for n in data):
                return {"ok": False, "error": "节点名已被占用"}

            old_name = target["name"]
            target["name"] = name
            target["description"] = (description or "").strip()
            target["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cls._save(data)

            if old_name != name:
                rename_node(old_name, name)

        return {"ok": True, "node": target}

    # ---------- 删除 ----------

    @classmethod
    def delete(cls, node_id: int, purge: bool = True) -> dict:
        with _lock:
            data = cls._load()
            target = None
            rest = []
            for n in data:
                if n.get("id") == node_id:
                    target = n
                else:
                    rest.append(n)
            if not target:
                return {"ok": False, "error": "节点不存在"}
            cls._save(rest)

            if purge:
                delete_node_data(target["name"])

        return {"ok": True, "node": target}

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
                    delete_node_data(t["name"])

        return {"ok": True, "deleted": targets, "count": len(targets)}
