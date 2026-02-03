"""
Celery Worker Configuration.

Handles asynchronous tasks like:
- Generating forecasts (processor intensive)
- Sending email notifications (io bound)
"""

import os
from celery import Celery
from app.config import settings

# Initialize Celery
celery_app = Celery(
    "retail_demand_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Import tasks module to register tasks
# (We'll create app/tasks.py next)
celery_app.autodiscover_tasks(['app'])
