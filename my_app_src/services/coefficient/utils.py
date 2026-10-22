# utils.py
"""
工具函数模块
"""

import sys
from .coefficient_config import SHOW_PROGRESS_BAR


def progress_iterator(iterable, desc=None, total=None, disable=None):
    """
    带进度条的迭代器包装器
    disable 参数优先级：如果传入 disable 则使用传入值，否则使用 config 中的 SHOW_PROGRESS_BAR
    """
    if disable is None:
        disable = not SHOW_PROGRESS_BAR
    try:
        from tqdm import tqdm

        if disable or not sys.stdout.isatty():
            return iterable
        return tqdm(iterable, desc=desc, total=total, leave=True)
    except ImportError:
        return iterable
