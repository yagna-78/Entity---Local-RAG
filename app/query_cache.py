"""
QUERY CACHE — In-Memory TTL Cache

Caches frequent baseline queries to avoid repeated DB hits.
TTL = 300 seconds (5 minutes), aligned with KPI scheduler cycle.
Thread-safe via simple dict + timestamp check.
"""

import time
import logging
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)

# Cache storage: {key: (value, expiry_timestamp)}
_cache: dict = {}
DEFAULT_TTL = 300  # 5 minutes


def get(key: str) -> Optional[Any]:
    """Fetch from cache if fresh. Returns None if expired or missing."""
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expiry = entry
    if time.time() > expiry:
        del _cache[key]
        logger.debug(f"Cache MISS (expired): {key}")
        return None
    logger.debug(f"Cache HIT: {key}")
    return value


def set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    """Store a value with TTL."""
    _cache[key] = (value, time.time() + ttl)


def get_or_compute(key: str, compute_fn: Callable, ttl: int = DEFAULT_TTL) -> Any:
    """
    Returns cached value if fresh, otherwise calls compute_fn(),
    caches the result, and returns it.
    """
    cached = get(key)
    if cached is not None:
        return cached
    
    value = compute_fn()
    set(key, value, ttl)
    return value


def invalidate(key: str):
    """Remove a specific key from cache."""
    _cache.pop(key, None)


def invalidate_all():
    """Clear entire cache."""
    _cache.clear()
    logger.info("Query cache cleared.")
