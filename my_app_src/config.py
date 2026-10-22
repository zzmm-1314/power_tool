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

    # ---------- Excel 数据目录 ----------
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOAD_DIR = os.path.join(DATA_DIR, "load")
    PRICE_DIR = os.path.join(DATA_DIR, "price")
    SPREAD_DIR = os.path.join(DATA_DIR, "spread")
    SETTLEMENT_DIR = os.path.join(DATA_DIR, "settlement")
    MONTHLY_DIR = os.path.join(DATA_DIR, "monthly")

    JSON_AS_ASCII = False
    # ---------- 临时数据 ----------
    TEMP_DATA_DIR = os.path.join(DATA_DIR, "temp")
    TEMP_AUTO_CLEAN = _bool("TEMP_AUTO_CLEAN", True)
    TEMP_CLEAN_INTERVAL = _int("TEMP_CLEAN_INTERVAL", 300)  # 秒
