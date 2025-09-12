# app/celery_config.py - Configurações específicas da app
from celery import current_app as celery
from celery.schedules import crontab

# ✅ Configurações específicas para tasks pesadas
celery.conf.update(
    task_always_eager=False,
    task_ignore_result=False,
    task_store_errors_even_if_ignored=True,
)

# ✅ AGENDAMENTOS COMPLETOS COM FALLBACK E STATUS
celery.conf.beat_schedule = {
    # SCRAPING PRINCIPAL E FALLBACK
    'buscar-publicacoes-dia': {
        'task': 'app.tasks.tarefa_buscar_publicacoes',
        'schedule': crontab(hour=18, minute=0),  # ← 18h - Principal
        'options': {'queue': 'scraping'}
    },
    'tentar-novamente-se-falhar': {
        'task': 'app.tasks.tentar_novamente_se_falhar',
        'schedule': crontab(hour=21, minute=0),  # ← 21h - Fallback
        'options': {'queue': 'scraping'}
    },
    
    # MONITORAMENTO E STATUS
    'verificar-status-sistema': {
        'task': 'app.tasks.verificar_status_sistema',
        'schedule': crontab(hour=7, minute=0),  # ← 7h - Status diário
        'options': {'queue': 'monitoring'}
    },
    
    # RELATÓRIOS E NOTIFICAÇÕES
    'enviar-relatorio-diario': {
        'task': 'app.tasks.enviar_relatorio_diario',
        'schedule': crontab(hour=8, minute=0),  # ← 8h - Relatório
        'options': {'queue': 'whatsapp'}
    },
    'verificar-novas-publicacoes': {
        'task': 'app.tasks.verificar_novas_publicacoes',
        'schedule': crontab(minute='*/30'),  # ← A cada 30min
        'options': {'queue': 'notifications'}
    },
    
    # HEALTH CHECK
    'health-check-diario': {
        'task': 'app.tasks.health_check',
        'schedule': crontab(hour='*/6'),  # ← A cada 6 horas
        'options': {'queue': 'monitoring'}
    }
}