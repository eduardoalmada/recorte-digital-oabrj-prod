import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    "recorte",
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_BROKER_URL"),
)

celery.conf.update(
    task_routes={'app.tasks.*': {'queue': 'default'}},
    timezone='America/Sao_Paulo',
    enable_utc=False,
)

celery.autodiscover_tasks(['app'])

# Ativa o Beat apenas quando este container for o beat
if os.getenv("IS_BEAT", "false").lower() == "true":
    from celery.schedules import crontab
    celery.conf.beat_schedule = {
        'buscar-publicacoes-dia': {
            'task': 'app.tasks.tarefa_buscar_publicacoes',
            'schedule': crontab(hour=15, minute=0),  # 15h Brasília
        },
        # ✅ ADICIONE ESTA NOVA TAREFA AQUI (DJEN EM HORÁRIO DIFERENTE)
        'buscar-djen-teste': {
            'task': 'app.tasks.tarefa_apenas_djen',
            'schedule': crontab(hour=16, minute=30),  # 16:30h - depois do DJERJ
        },
    }
