import time
import logging
import hashlib
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from .celery_app import celery
from .processing import process_task
from .database import SessionLocal
from .models import Job
from datetime import datetime, timezone
from .redis_client import redis_client
from .metrics import increment, record_duration

logger = logging.getLogger(__name__)

def make_cache_key(task_type: str, input_text: str) -> str:
    content = f"{task_type}:{input_text}"
    return f"result:{hashlib.sha256(content.encode()).hexdigest()}"

@celery.task(bind=True, max_retries=3, default_retry_delay=5, time_limit=30, soft_time_limit=25)
def process_job(self, job_id: str):
    start_time = time.time()
    logger.info(f"Picked up job {job_id} (attempt {self.request.retries + 1}/{self.max_retries + 1})")

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning(f"Job {job_id} not found — skipping")
            return

        if job.status == "completed":
            logger.info(f"Job {job_id} already completed — skipping")
            return

        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        cache_key = make_cache_key(job.task_type, job.input_text)
        cached_result = redis_client.get(cache_key)

        if cached_result:
            result =cached_result
            logger.info(f"Job {job_id} served from cache")
        else:
            result = process_task(job.task_type, job.input_text)
            redis_client.setex(cache_key, 3600, result)
            logger.info(f"Job {job_id} result cached for 1 hour")
            

        job.result = result
        job.status = "completed"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        duration = round(time.time() - start_time, 2)
        logger.info(f"Job {job_id} completed in {duration}s")
        increment("jobs_completed")
        record_duration("job_processing", duration)

    except SoftTimeLimitExceeded:
        db.rollback()
        logger.error(f"Job {job_id} timed out after 25 seconds")
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.retry_count += 1
                job.updated_at = datetime.now(timezone.utc)
                try:
                    job.status = "pending"
                    db.commit()
                    countdown = 5 * (2 ** self.request.retries)
                    logger.warning(f"Job {job_id} timed out — retrying in {countdown}s ({job.retry_count}/{self.max_retries + 1})")
                    raise self.retry(countdown=countdown)
                except MaxRetriesExceededError:
                    job.status = "failed"
                    increment("jobs_failed")
                    job.failed_reason = "Timed out on all attempts"
                    db.commit()
                    logger.error(f"Job {job_id} permanently failed — timed out on all attempts")
        except MaxRetriesExceededError:
            pass
        except Exception as inner_e:
            logger.error(f"Could not update job {job_id} after timeout: {inner_e}")

    except Exception as e:
        db.rollback()
        duration = round(time.time() - start_time, 2)

        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.retry_count += 1
                job.updated_at = datetime.now(timezone.utc)

                try:
                    job.status = "pending"
                    db.commit()
                    countdown = 5 * (2 ** self.request.retries)
                    logger.warning(f"Job {job_id} failed after {duration}s: {e} — retrying in {countdown}s ({job.retry_count}/{self.max_retries + 1})")
                    raise self.retry(exc=e, countdown=countdown)
                except MaxRetriesExceededError:
                    job.status = "failed"
                    increment("jobs_failed")
                    job.failed_reason = str(e)
                    db.commit()
                    logger.error(f"Job {job_id} permanently failed after {job.retry_count} attempts: {e}")

        except MaxRetriesExceededError:
            pass
        except Exception as inner_e:
            logger.error(f"Could not update job {job_id}: {inner_e}")

    finally:
        db.close()