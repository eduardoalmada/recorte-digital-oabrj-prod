import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    "recorte",
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_BROKER_URL")
)

celery.conf.update(
    task_routes={
        'app.tasks.*': {'queue': 'default'},
    },
    timezone='America/Sao_Paulo',
    enable_utc=False,
)

celery.autodiscover_tasks(['app'])

# Força o registro explícito das tasks
import app.tasks  # noqa

from celery.schedules import crontab

celery.conf.beat_schedule = {
    'buscar-publicacoes-a-cada-5-min': {
        'task': 'app.tasks.tarefa_buscar_publicacoes',
        'schedule': crontab(hour=15, minute=0),  # 15h todos os dias
    },
}
