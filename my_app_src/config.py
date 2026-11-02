import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


class Config:
    # ---------- Flask ----------
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = _bool("FLASK_DEBUG", False)
    SECRET_KEY = os.getenv("SECRET_KEY", "power-tool-secret")

    # ---------- 上传 ----------
    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 50) * 1024 * 1024

    # ---------- 数据目录（非 Excel 业务文件：节点清单、模板、配置等） ----------
    DATA_DIR = os.path.join(BASE_DIR, "data")

    JSON_AS_ASCII = False

    # ---------- 业务数据库（上传解析后的数据入库、各模块读取的唯一来源） ----------
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = _int("DB_PORT", 3306)
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_NAME = os.getenv("DB_NAME", "power_tool")
