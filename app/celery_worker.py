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

from celery.schedules import crontab

celery.conf.beat_schedule = {
    'buscar-publicacoes-diariamente': {
        'task': 'app.tasks.tarefa_buscar_publicacoes',
        'schedule': crontab(hour=8, minute=0),  # ⏰ 08:00 da manhã todos os dias
    },
}
