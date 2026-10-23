"""统一管理安装目录与本地镜像目录"""

import sys
from pathlib import Path


def get_local_mirror_dir() -> Path:
    """
    本地镜像目录（业务实际读取的位置）：
      开发 / 打包后都是 my_app_src/data/temp_mirror
    """
    d = Path(__file__).resolve().parent.parent / "data" / "temp_mirror"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)
