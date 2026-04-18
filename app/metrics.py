import time
from .redis_client import redis_client

METRICS_PREFIX = "metrics:"


def increment(name: str, amount: int = 1):
    """Count something. Example: increment('jobs_completed')"""
    redis_client.incr(f"{METRICS_PREFIX}{name}", amount)


def record_duration(name: str, seconds: float):
    """Record a duration. Stores total and count so you can compute average."""
    pipe = redis_client.pipeline()
    pipe.incrbyfloat(f"{METRICS_PREFIX}{name}_total_seconds", seconds)
    pipe.incr(f"{METRICS_PREFIX}{name}_count")
    pipe.execute()


def get_all_metrics() -> dict:
    """Read all metrics from Redis."""
    keys = redis_client.keys(f"{METRICS_PREFIX}*")
    if not keys:
        return {}
    
    result = {}
    for key in keys:
        clean_key = key.replace(METRICS_PREFIX, "")
        value = redis_client.get(key)
        try:
            result[clean_key] = float(value)
        except (TypeError, ValueError):
            result[clean_key] = value
    
    return result