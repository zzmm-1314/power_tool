import logging
import logging.handlers
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Optional

from desktop_app_source_updater import (
    UpdateConfig,
    format_update_message,
    run_startup_update,
)

# ==================== 路径配置 ====================
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    APP_ROOT = Path(__file__).resolve().parent

SRC_DIR = APP_ROOT / "my_app_src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

USER_STATE_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache")

os.environ.setdefault("POWER_TOOL_UPDATE_TIMEOUT_SECONDS", "10")


# ==================== 日志配置 ====================
LOG_DIR = APP_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "launcher.log"


def _setup_logger() -> logging.Logger:
    lg = logging.getLogger("launcher")
    lg.setLevel(logging.INFO)
    lg.propagate = False

    if lg.handlers:
        return lg

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件日志：5MB 轮转，保留 3 份
    try:
        fh = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        lg.addHandler(fh)
    except Exception as e:
        # 日志文件不可写时，不影响启动
        try:
            sys.stderr.write(f"[launcher] 日志文件初始化失败: {e}\n")
        except Exception:
            pass

    # 控制台日志：windowed 打包模式下 sys.stderr 为 None，需要跳过
    if sys.stderr is not None:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(fmt)
        lg.addHandler(ch)

    return lg


logger = _setup_logger()


# ==================== 模态更新窗口 ====================
class UpdateWindow:
    """启动时的更新检查与下载窗口"""

    def __init__(self, config: UpdateConfig):
        self.config = config
        self.user_skip = False
        self.result = None
        self._window: Optional[tk.Tk] = None
        self._progress: Optional[ttk.Progressbar] = None
        self._status_var: Optional[tk.StringVar] = None
        self._btn_skip: Optional[tk.Button] = None
        self._btn_frame: Optional[tk.Frame] = None

    def _build_ui(self):
        root = tk.Tk()
        root.title("电力工具助手")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        w, h = 440, 190
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(
            root,
            text="电力工具助手",
            font=("Microsoft YaHei", 14, "bold"),
            fg="#1f2d3d",
        ).pack(pady=(20, 6))

        self._status_var = tk.StringVar(value="正在检查更新...")
        tk.Label(
            root,
            textvariable=self._status_var,
            font=("Microsoft YaHei", 10),
            fg="#606266",
            wraplength=380,
            justify="center",
        ).pack(pady=(4, 12))

        self._progress = ttk.Progressbar(root, mode="indeterminate", length=340)
        self._progress.pack(pady=(0, 14))

        self._btn_frame = tk.Frame(root)
        self._btn_frame.pack(pady=(0, 16))

        self._btn_skip = tk.Button(
            self._btn_frame,
            text="跳过更新",
            width=10,
            command=self._on_skip,
        )
        self._btn_skip.pack(side="left", padx=8)

        self._window = root

    def _set_status(self, text: str):
        if self._window is None:
            return
        try:
            self._window.after(0, lambda: self._status_var.set(text))
        except tk.TclError:
            pass

    def _on_skip(self):
        logger.info("用户点击「跳过更新」")
        self.user_skip = True
        self._set_status("正在跳过更新，稍后自动启动...")

    def _on_close(self):
        logger.info("用户关闭更新窗口（视同跳过）")
        self.user_skip = True
        if self._window:
            try:
                self._window.destroy()
            except tk.TclError:
                pass

    def _run_update(self):
        try:
            self.result = run_startup_update(
                self.config,
                force_check="--check-update" in sys.argv,
            )
        except Exception as e:
            logger.exception("更新线程异常")
            self.result = {"error": str(e), "status": "error"}
        finally:
            if self._window:
                try:
                    self._window.after(0, self._on_update_finished)
                except tk.TclError:
                    pass

    def _on_update_finished(self):
        if self._progress:
            try:
                self._progress.stop()
            except tk.TclError:
                pass

        r = self.result or {}
        error = r.get("error") if isinstance(r, dict) else None
        status = r.get("status") if isinstance(r, dict) else ""

        msg = ""
        try:
            msg = format_update_message(r) or ""
        except Exception:
            logger.exception("format_update_message 失败")

        if error:
            logger.error("更新失败: %s", error)
            self._set_status(f"更新失败：{error}\n将使用当前版本启动。")
        elif status in ("updated", "update_applied"):
            logger.info("更新成功")
            self._set_status("更新完成，即将启动应用...")
        elif msg:
            logger.info("更新结果: %s", msg)
            self._set_status(msg)
        else:
            logger.info("已是最新版本")
            self._set_status("已是最新版本")

        if self._btn_skip:
            self._btn_skip.config(state="disabled")

        if self._btn_frame and self._window:
            try:
                tk.Button(
                    self._btn_frame,
                    text="启动应用",
                    width=10,
                    command=self._window.destroy,
                ).pack(side="left", padx=8)
            except tk.TclError:
                pass

        if self._window:
            try:
                self._window.after(2000, self._window.destroy)
            except tk.TclError:
                pass

    def _bind_global(self):
        global _CURRENT_WINDOW
        _CURRENT_WINDOW = self

    def _unbind_global(self):
        global _CURRENT_WINDOW
        _CURRENT_WINDOW = None

    def run(self):
        self._build_ui()
        self._bind_global()

        if self._progress:
            self._progress.start(12)

        logger.info("更新窗口已打开，APP_ROOT=%s, SRC_DIR=%s", APP_ROOT, SRC_DIR)
        threading.Thread(target=self._run_update, daemon=True).start()

        try:
            self._window.mainloop()
        finally:
            self._unbind_global()

        logger.info("更新窗口已关闭，user_skip=%s", self.user_skip)
        return self.user_skip


_CURRENT_WINDOW: Optional[UpdateWindow] = None


# ==================== 更新回调 ====================
def _on_update_available(installed_version, target_version):
    logger.info("发现新版本: %s -> %s", installed_version, target_version)
    w = _CURRENT_WINDOW
    if w is not None:
        w._set_status(f"发现新版本 {target_version}，正在下载...")


# ==================== 更新配置 ====================
update_config = UpdateConfig(
    app_name="power_tool",
    app_root=APP_ROOT,
    installed_version_file=str(SRC_DIR / "__init__.py"),
    latest_release_url="https://github.com/zzmm-1314/power_tool/releases/latest",
    asset_prefix="power_tool_update_",
    allowed_payload_paths=("my_app_src/", "static/"),
    check_state_file=USER_STATE_ROOT / "power_tool" / "update-check.json",
    skip_update_env="POWER_TOOL_SKIP_UPDATE",
    update_zip_url_env="POWER_TOOL_UPDATE_ZIP_URL",
    timeout_env="POWER_TOOL_UPDATE_TIMEOUT_SECONDS",
    force_check_env="POWER_TOOL_FORCE_UPDATE_CHECK",
    on_update_available=_on_update_available,
)


# ==================== 主入口 ====================
def main():
    logger.info("=" * 60)
    logger.info("启动器开始运行")
    logger.info("frozen=%s", getattr(sys, "frozen", False))
    logger.info("APP_ROOT=%s", APP_ROOT)
    logger.info("SRC_DIR=%s", SRC_DIR)
    logger.info("LOG_FILE=%s", LOG_FILE)

    if os.environ.get("POWER_TOOL_SKIP_UPDATE"):
        logger.info("POWER_TOOL_SKIP_UPDATE 已设置，跳过更新窗口")
    else:
        try:
            w = UpdateWindow(update_config)
            w.run()
        except Exception as e:
            logger.exception("更新窗口异常")
            try:
                messagebox.showwarning(
                    "电力工具助手",
                    f"更新检查失败：{e}\n\n将跳过更新直接启动。",
                )
            except Exception:
                logger.exception("弹窗提示也失败了")

    logger.info("即将启动业务应用")
    try:
        from app import main as app_main

        app_main()
    except Exception:
        logger.exception("业务应用启动失败")
        # 打包后业务异常时给出提示，避免白屏直接退出
        try:
            messagebox.showerror(
                "电力工具助手",
                "应用启动失败，详情请查看 logs\\launcher.log",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
