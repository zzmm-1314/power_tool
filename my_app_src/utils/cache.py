"""轻量级内存缓存装饰器（无第三方依赖）"""

import threading
import time
from functools import wraps

_CACHE_STORE = {}
_LOCK = threading.Lock()


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
                        return result
                    _CACHE_STORE.pop(key, None)

            result = func(*args, **kwargs)

            with _LOCK:
                _CACHE_STORE[key] = (result, time.time())  # 用执行完的时间

            return result

        return wrapper

    return decorator


def clear_cache():
    with _LOCK:
        _CACHE_STORE.clear()
