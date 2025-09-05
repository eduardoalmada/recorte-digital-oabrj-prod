# app/celery_config.py - Configurações específicas da app
from celery import current_app as celery

# ✅ Configurações específicas para tasks pesadas
celery.conf.update(
    task_always_eager=False,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
)

# ✅ Health check para workers
@celery.task(name='app.tasks.health_check')
def health_check():
    """Task simples para verificar se worker está vivo"""
    return {'status': 'healthy', 'service': 'celery_worker'}
