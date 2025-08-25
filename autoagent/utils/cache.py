# autoagent/utils/cache.py
import time
from functools import lru_cache, wraps
from typing import Callable

def ttl_cache(ttl_seconds: int = 300):
    """
    Decorator: łączy lru_cache z czasem ważności (TTL).
    - Po upływie ttl_seconds cache jest czyszczony przy następnym wywołaniu.
    - wrapped.cache_clear() pozwala ręcznie wyczyścić cache.
    """
    def decorator(fn: Callable):
        cached = lru_cache(maxsize=1)(fn)
        last_filled_at = {"t": 0.0}

        @wraps(fn)
        def wrapped(*args, **kwargs):
            now = time.time()
            if now - last_filled_at["t"] > ttl_seconds:
                cached.cache_clear()
                last_filled_at["t"] = now
            return cached(*args, **kwargs)

        def cache_clear():
            cached.cache_clear()
            last_filled_at["t"] = 0.0

        wrapped.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapped
    return decorator
