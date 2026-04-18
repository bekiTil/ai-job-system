from datetime import datetime, timezone, timedelta
from .database import SessionLocal
from .models import Job
from .tasks import process_job

MAX_RETRIES = 3


def check_stale_jobs():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)

        stale_jobs = db.query(Job).filter(
            Job.status == "running",
            Job.updated_at < cutoff
        ).all()

        for job in stale_jobs:
            if job.retry_count >= MAX_RETRIES:
                print(f"Job {job.id} exceeded {MAX_RETRIES} retries — marking as failed")
                job.status = "failed"
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
            else:
                job.retry_count += 1
                job.status = "pending"
                job.updated_at = datetime.now(timezone.utc)
                db.commit()

                process_job.delay(str(job.id))
                print(f"Requeued job {job.id} (retry {job.retry_count}/{MAX_RETRIES})")

        if not stale_jobs:
            print("No stale jobs found")

    finally:
        db.close()


if __name__ == "__main__":
    check_stale_jobs()