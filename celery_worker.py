# celery.py - Ponto de entrada principal do Celery
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
    task_time_limit=3600,  # 1 hora para tasks pesadas
    task_soft_time_limit=3300,  # 55min para graceful shutdown
    worker_max_tasks_per_child=50,  # Previne memory leaks
    worker_prefetch_multiplier=1,  # Justo para tasks longas
    task_acks_late=True,  # ✅ Previne perda de tasks
    task_reject_on_worker_lost=True,
)

# ✅ Configuração do Beat (apenas quando variável IS_BEAT=true)
if os.getenv("IS_BEAT", "false").lower() == "true":
    from celery.schedules import crontab
    celery.conf.beat_schedule = {
        'buscar-publicacoes-dia': {
            'task': 'app.tasks.tarefa_buscar_publicacoes',  # ✅ TASK EXISTENTE
            'schedule': crontab(hour=15, minute=0),  # 15h Brasília
            'options': {'queue': 'default'}
        }
        # ❌ REMOVIDO: 'buscar-djen-teste' (task não existe)
    }
    print("✅ Celery Beat configurado e ativo")

# ✅ Auto-discover para tasks em outros módulos
celery.autodiscover_tasks(['app'], force=True)

# ✅ Exporta a instância para ser importada pelo main.py
celery_app = celery  # <-- ESTA LINHA DEVE EXISTIR

if __name__ == '__main__':
    celery.start()
