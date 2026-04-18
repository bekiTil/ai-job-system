import logging
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from .models import User, Job
from .schemas import UserCreate, UserResponse, JobCreate, JobResponse, ALLOWED_TASK_TYPES
from .tasks import process_job
from .redis_client import redis_client
from .logging_config import setup_logging
from .metrics import get_all_metrics
from .middleware import RequestLoggingMiddleware
from .dashboard import get_dashboard

setup_logging()

logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("uvicorn.error").handlers = []


app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)


def check_rate_limit(user_id: str, limit: int = 10, window: int = 60):
    key = f"ratelimit:{user_id}:{int(time.time()) // window}"
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    return current <= limit

def check_queue_depth(max_depth: int = 1000) -> bool:
    queue_length = redis_client.llen("celery")
    return queue_length < max_depth

@app.get("/health")
def health_check():
    return {"status": "ok"}
@app.get("/metrics")
def metrics():
    return get_all_metrics()
@app.get("/dashboard")
def dashboard():
    return get_dashboard()

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    new_user = User(email=user_data.email, name=user_data.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
@app.post("/jobs", response_model=JobResponse, status_code=201)
def submit_job(job_data: JobCreate, db: Session = Depends(get_db)):
    if job_data.task_type not in ALLOWED_TASK_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_type. Must be one of: {', '.join(ALLOWED_TASK_TYPES)}"
        )

    user = db.query(User).filter(User.id == job_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not check_rate_limit(str(job_data.user_id)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 jobs per minute. Try again later."
        )
    if not check_queue_depth():
        raise HTTPException(
            status_code=503,
            detail="System is busy. Too many jobs in queue. Please try again later."
        )

    new_job = Job(
        user_id=job_data.user_id,
        task_type=job_data.task_type,
        input_text=job_data.input_text,
        status="pending",
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    process_job.delay(str(new_job.id))

    return new_job

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    user_id: UUID = Query(..., description="Filter by user ID"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    jobs = db.query(Job).filter(Job.user_id == user_id).order_by(Job.created_at.desc()).all()
    return jobs


@app.get("/users", response_model=list[UserResponse])
def list_users(db: Session= Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users