import os
import sys
from pathlib import Path

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

# 同时加入两个路径：SRC_DIR 让业务模块成为顶级，APP_ROOT 让 import my_app_src 成功
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

USER_STATE_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache")


# ==================== 启动前诊断 ====================
def _diagnose():
    print(f"[launcher] frozen={getattr(sys, 'frozen', False)}", flush=True)
    print(f"[launcher] APP_ROOT={APP_ROOT}", flush=True)
    print(f"[launcher] SRC_DIR={SRC_DIR}", flush=True)
    print(f"[launcher] SRC_DIR exists={SRC_DIR.is_dir()}", flush=True)
    init_file = SRC_DIR / "__init__.py"
    app_file = SRC_DIR / "app.py"
    print(f"[launcher] __init__.py exists={init_file.is_file()}", flush=True)
    print(f"[launcher] app.py exists={app_file.is_file()}", flush=True)
    if init_file.is_file():
        try:
            ns = {}
            exec(init_file.read_text(encoding="utf-8"), ns)
            print(f"[launcher] __version__={ns.get('__version__')!r}", flush=True)
        except Exception as e:
            print(f"[launcher] 读取 __version__ 失败: {e}", flush=True)


_diagnose()


# ==================== 更新回调 ====================
def show_update_available(installed_version, target_version):
    print(
        f"[startup-update] updating from {installed_version} to {target_version}",
        flush=True,
    )


# ==================== 更新配置 ====================
update_config = UpdateConfig(
    app_name="power_tool",
    app_root=APP_ROOT,
    installed_version_file=str(SRC_DIR / "__init__.py"),
    latest_release_url="https://github.com/zzmm-1314/power_tool/releases/latest",
    asset_prefix="power_tool_update_",
    allowed_payload_paths=("my_app_src/", "static/"),  # ← 加上 static/
    check_state_file=USER_STATE_ROOT / "power_tool" / "update-check.json",
    skip_update_env="POWER_TOOL_SKIP_UPDATE",
    update_zip_url_env="POWER_TOOL_UPDATE_ZIP_URL",
    timeout_env="POWER_TOOL_UPDATE_TIMEOUT_SECONDS",
    force_check_env="POWER_TOOL_FORCE_UPDATE_CHECK",
    on_update_available=show_update_available,
)

result = run_startup_update(
    update_config,
    force_check="--check-update" in sys.argv,
)
message = format_update_message(result)
if message:
    print(f"[startup-update] {message}", flush=True)


# ==================== 启动业务应用 ====================
from app import main  # noqa: E402

if __name__ == "__main__":
    main()
