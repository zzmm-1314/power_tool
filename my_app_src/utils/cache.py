"""轻量级内存缓存装饰器（无第三方依赖）"""

import threading
import time
from functools import wraps
import copy

_CACHE_STORE = {}
_LOCK = threading.Lock()
_CACHE_MAX = 500


def ttl_cache(seconds=7200):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            with _LOCK:
                entry = _CACHE_STORE.get(key)
                if entry is not None:
                    result, timestamp = entry
                    if time.time() - timestamp < seconds:
                        return copy.deepcopy(result)  # ← 返回副本
                    _CACHE_STORE.pop(key, None)
            result = func(*args, **kwargs)
            with _LOCK:
                if len(_CACHE_STORE) >= _CACHE_MAX:
                    # 淘汰最旧的一批
                    oldest = sorted(_CACHE_STORE.items(), key=lambda kv: kv[1][1])[
                        : len(_CACHE_STORE) // 4
                    ]
                    for k, _ in oldest:
                        _CACHE_STORE.pop(k, None)
                _CACHE_STORE[key] = (copy.deepcopy(result), time.time())  # ← 存副本
            return result

        return wrapper

    return decorator


def clear_cache(prefix=None):
    """清空缓存。

    prefix 为空：清空全部；
    prefix 为字符串或字符串序列：只清理函数名以该前缀开头的缓存条目
    （键格式为 "函数名:参数"，因此可按函数粒度失效）。
    """
    with _LOCK:
        if not prefix:
            _CACHE_STORE.clear()
            return
        prefixes = (prefix,) if isinstance(prefix, str) else tuple(prefix)
        keys = [
            k
            for k in _CACHE_STORE
            if any(k.startswith(f"{p}:") for p in prefixes if p)
        ]
        for k in keys:
            _CACHE_STORE.pop(k, None)
