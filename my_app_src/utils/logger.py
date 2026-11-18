"""统一日志入口：替代散落在各模块里的 print

用法：
    from utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("启动完成")
    logger.warning("解析失败: %s", e)

输出目的地：
- 控制台（stderr）
- 文件 <APP_ROOT>/logs/app.log（滚动：单文件 2MB，保留 3 份）

可调环境变量（写在 my_app_src/.env 里即可）：
- POWER_TOOL_LOG_LEVEL = DEBUG | INFO | WARNING | ERROR   （默认 INFO）
- POWER_TOOL_LOG_FILE  = 自定义日志文件绝对路径；填 off / none 则不写文件
"""

import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path

_LEVEL_NAMES = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

DATE_FMT = "%Y-%m-%d %H:%M:%S"
FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3

_lock = threading.Lock()
_configured = False


def _app_root() -> Path:
    """与 app.py 保持一致：打包后取 exe 所在目录，开发时取项目根目录"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def default_log_file() -> Path:
    return _app_root() / "logs" / "app.log"


def _resolve_level() -> int:
    raw = (os.getenv("POWER_TOOL_LOG_LEVEL") or "INFO").strip().upper()
    return _LEVEL_NAMES.get(raw, logging.INFO)


def _resolve_log_file() -> Path | None:
    """返回 None 表示不写文件"""
    raw = (os.getenv("POWER_TOOL_LOG_FILE") or "").strip()
    if not raw:
        return default_log_file()
    if raw.lower() in ("off", "none", "false", "0", ""):
        return None
    return Path(raw)


def _console_handler(level: int) -> logging.Handler | None:
    """windowed 打包模式下 sys.stderr 为 None，此时跳过控制台输出"""
    if sys.stderr is None:
        return None
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(FMT, DATE_FMT))
    return handler


def _file_handler(path: Path, level: int) -> logging.Handler | None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            str(path),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(FMT, DATE_FMT))
        return handler
    except OSError as e:
        # 日志目录不可写时降级为只输出控制台，不能让业务因此中断
        logging.getLogger("power_tool.logger").warning(
            "日志文件不可用（%s），仅输出控制台：%s", e, path
        )
        return None


def setup_logging(force: bool = False) -> logging.Logger:
    """配置根 logger（幂等，重复调用不会叠加 handler）"""
    global _configured
    with _lock:
        if _configured and not force:
            return logging.getLogger()

        level = _resolve_level()
        root = logging.getLogger()
        root.setLevel(level)
        for old in list(root.handlers):
            root.removeHandler(old)

        console = _console_handler(level)
        if console is not None:
            root.addHandler(console)

        log_file = _resolve_log_file()
        if log_file is not None:
            handler = _file_handler(log_file, level)
            if handler is not None:
                root.addHandler(handler)

        # werkzeug 每个请求都打一行，写进文件太吵，只保留警告以上
        logging.getLogger("werkzeug").setLevel(max(level, logging.WARNING))

        # 第三方库的 INFO 与业务无关，统一降噪
        for noisy in (
            "numexpr",
            "PIL",
            "urllib3",
            "matplotlib",
            "pdfminer",
            "pdfplumber",
        ):
            logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

        _configured = True
        return root


def get_logger(name: str | None = None) -> logging.Logger:
    """获取 logger；首次调用时自动完成配置"""
    setup_logging()
    return logging.getLogger(name or "power_tool")
