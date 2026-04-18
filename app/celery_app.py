import os
from celery import Celery 

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


celery = Celery(
     "ai_jobs",
     broker=f"{REDIS_URL}/0",
     include=["app.tasks"]
)

import logging
from celery.signals import setup_logging as celery_setup_logging
from .logging_config import get_json_handler

@celery_setup_logging.connect
def configure_celery_logging(**kwargs):
    handler = get_json_handler()
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)