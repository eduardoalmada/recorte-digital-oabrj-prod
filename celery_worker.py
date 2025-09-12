# celery_worker.py - Ponto de entrada principal do Celery
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# ✅ Configuração robusta para produção
celery = Celery(
    "recorte_digital",
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_BROKER_URL"),
    include=['app.tasks']  # ✅ APENAS O MÓDULO PRINCIPAL
)

# ✅ Configurações de produção
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=False,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# ✅ Auto-discover para tasks em outros módulos
celery.autodiscover_tasks(['app'], force=True)

# ✅ Exporta a instância para ser importada pelo main.py
celery_app = celery

if __name__ == '__main__':
    celery.start()