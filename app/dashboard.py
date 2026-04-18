from .redis_client import redis_client
from .metrics import METRICS_PREFIX


def get_dashboard():
    keys = redis_client.keys(f"{METRICS_PREFIX}*")
    raw = {}
    for key in keys:
        clean_key = key.replace(METRICS_PREFIX, "")
        value = redis_client.get(key)
        try:
            raw[clean_key] = float(value)
        except (TypeError, ValueError):
            raw[clean_key] = 0

    jobs_completed = raw.get("jobs_completed", 0)
    jobs_failed = raw.get("jobs_failed", 0)
    jobs_total = jobs_completed + jobs_failed

    processing_total = raw.get("job_processing_total_seconds", 0)
    processing_count = raw.get("job_processing_count", 0)
    avg_processing = round(processing_total / processing_count, 3) if processing_count > 0 else 0

    http_total = raw.get("http_requests_total", 0)
    http_errors = raw.get("http_errors_total", 0)
    error_rate = round((http_errors / http_total) * 100, 2) if http_total > 0 else 0

    request_total = raw.get("http_request_total_seconds", 0)
    request_count = raw.get("http_request_count", 0)
    avg_request = round(request_total / request_count, 4) if request_count > 0 else 0

    return {
        "jobs": {
            "completed": int(jobs_completed),
            "failed": int(jobs_failed),
            "total": int(jobs_total),
            "failure_rate_percent": round((jobs_failed / jobs_total) * 100, 2) if jobs_total > 0 else 0,
        },
        "processing": {
            "average_seconds": avg_processing,
            "total_seconds": round(processing_total, 2),
        },
        "http": {
            "total_requests": int(http_total),
            "total_errors": int(http_errors),
            "error_rate_percent": error_rate,
            "average_response_seconds": avg_request,
        },
    }