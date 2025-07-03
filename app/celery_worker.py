from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    'recorte',
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_BROKER_URL")
)

celery.conf.timezone = 'America/Sao_Paulo'

from app.tasks import tarefa_buscar_publicacoes  # noqa
