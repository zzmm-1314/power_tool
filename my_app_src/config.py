import os
import sys
from dotenv import load_dotenv


def _find_env_path():
    # 1. 优先找当前代码同级目录（开发环境、或打包后放在 my_app_src 里）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        return env_path

    # 2. 打包环境：exe 所在目录 / my_app_src / .env
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        env_path = os.path.join(exe_dir, "my_app_src", ".env")
        if os.path.exists(env_path):
            return env_path

        # 3. 兜底：exe 同级目录 / .env
        env_path = os.path.join(exe_dir, ".env")
        if os.path.exists(env_path):
            return env_path

    # 4. 源码环境容错：上一级目录 / .env
    parent_path = os.path.join(os.path.dirname(current_dir), ".env")
    if os.path.exists(parent_path):
        return parent_path

    return None


_env_path = _find_env_path()
if _env_path:
    load_dotenv(_env_path, override=False)
    print(f"[Config] 已加载环境变量文件: {_env_path}")
else:
    # 尝试默认加载
    load_dotenv(override=True)
    print("[Config] 警告: 未找到 .env 文件，使用默认环境变量")


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


class Config:
    # 无论是源码还是打包环境，BaseDir 都指向代码所在目录（即 my_app_src）
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # ---------- Flask ----------
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = _bool("FLASK_DEBUG", False)
    SECRET_KEY = os.getenv("SECRET_KEY", "power-tool-secret")
    # ---------- 端口 ----------
    FLASK_PORT = _int("FLASK_PORT", 5000)

    # ---------- JWT ----------
    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_EXPIRE_HOURS = _int("JWT_EXPIRE_HOURS", 24)
    # ---------- 上传 ----------
    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 50) * 1024 * 1024

    # ---------- 数据目录（非 Excel 业务文件：节点清单、模板、配置等） ----------
    DATA_DIR = os.path.join(BASE_DIR, "data")
    # Flask < 2.3 使用此键；Flask >= 2.3 请用 app.json.ensure_ascii = False
    JSON_AS_ASCII = False

    # ========== 江苏库（投标空间业务库 - 浙江省数据） ==========
    JS_DB_HOST = os.getenv("JS_DB_HOST", "")
    JS_DB_PORT = _int("JS_DB_PORT", 13307)
    JS_DB_USER = os.getenv("JS_DB_USER", "")
    JS_DB_PASS = os.getenv("JS_DB_PASS", "")
    JS_DB_NAME = os.getenv("JS_DB_NAME", "power_js")

    # 浙江临时库
    ZJ_DB_HOST = os.getenv("ZJ_DB_HOST", "")
    ZJ_DB_PORT = _int("ZJ_DB_PORT", 13306)
    ZJ_DB_USER = os.getenv("ZJ_DB_USER", "")
    ZJ_DB_PASS = os.getenv("ZJ_DB_PASS", "")
    ZJ_DB_NAME = os.getenv("ZJ_DB_NAME", "power_zj")
    # 是否禁用 SSL 连接
    SSL_DISABLED = _bool("SSL_DISABLED", True)
