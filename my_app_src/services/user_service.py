"""用户信息存储服务：读写 data/users.json"""

import os
import json
import threading
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

_LOCK = threading.Lock()
USERS_FILE = os.path.join(Config.DATA_DIR, "users.json")


def _ensure_file() -> None:
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": []}, f, ensure_ascii=False, indent=2)


def _load() -> dict:
    _ensure_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_user(username: str) -> dict | None:
    for u in _load().get("users", []):
        if u["username"] == username:
            return u
    return None


def create_user(username: str, password: str, role: str = "user"):
    """返回 (user, None) 或 (None, 错误信息)"""
    with _LOCK:
        data = _load()
        users = data.setdefault("users", [])
        if any(u["username"] == username for u in users):
            return None, "用户名已存在"
        user = {
            "username": username,
            "passwordHash": generate_password_hash(password),
            "role": role,
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        users.append(user)
        _save(data)
        return user, None


def verify_user(username: str, password: str) -> dict | None:
    user = find_user(username)
    if not user:
        return None
    if not check_password_hash(user["passwordHash"], password):
        return None
    return user


def ensure_default_admin() -> None:
    """首次启动时，写入默认管理员账号 admin / admin123"""
    if find_user("admin") is None:
        create_user("admin", "admin123", role="admin")
