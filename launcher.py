# launcher.py
import os
import sys
from pathlib import Path

from desktop_app_source_updater import (
    UpdateConfig,
    format_update_message,
    run_startup_update,
)

# ==================== 路径配置 ====================
APP_ROOT = Path(__file__).resolve().parent  # exe 所在目录
USER_STATE_ROOT = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache")

# 确保 my_app_src 在 sys.path 中
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


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
    installed_version_file="my_app_src/__init__.py",  # 版本号所在文件
    latest_release_url="https://github.com/zzmm-1314/power_tool.git",  # 替换为你的仓库
    asset_prefix="power_tool_update_",  # Release 资产名前缀
    allowed_payload_paths=("my_app_src/",),  # 只允许更新此目录
    check_state_file=USER_STATE_ROOT / "power_tool" / "update-check.json",
    skip_update_env="POWER_TOOL_SKIP_UPDATE",
    update_zip_url_env="POWER_TOOL_UPDATE_ZIP_URL",
    timeout_env="POWER_TOOL_UPDATE_TIMEOUT_SECONDS",
    force_check_env="POWER_TOOL_FORCE_UPDATE_CHECK",
    on_update_available=show_update_available,
)

# ==================== 执行更新（必须在导入业务代码之前） ====================
result = run_startup_update(
    update_config,
    force_check="--check-update" in sys.argv,
)
message = format_update_message(result)
if message:
    print(f"[startup-update] {message}", flush=True)

# ==================== 启动业务应用 ====================
from my_app_src.app import main  # 从外部源码导入

if __name__ == "__main__":
    main()
