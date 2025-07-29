from celery import shared_task
from app.scrapers.scraper_djerj_selenium import processar_publicacoes_djerj

@shared_task
def tarefa_buscar_publicacoes():
    print("🔎 Iniciando busca de publicações no DJERJ...")
    processar_publicacoes_djerj()
