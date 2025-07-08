import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    "recorte",
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_BROKER_URL")
)

celery.autodiscover_tasks(['app'])

# Força o registro das tasks (sem causar import circular)
import app.tasks  # noqa
