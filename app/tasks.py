from app.celery_worker import celery
from app.utils.datajud_client import buscar_publicacoes

@celery.task
def tarefa_buscar_publicacoes():
    buscar_publicacoes()
