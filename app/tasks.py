from app.scrapers.scraper_djerj_selenium import processar_publicacoes_djerj
from app import create_app
from app.celery_worker import celery

@celery.task(name="app.tasks.tarefa_buscar_publicacoes")
def tarefa_buscar_publicacoes():
    print("🔎 Iniciando busca de publicações no DJERJ...")
    app = create_app()
    with app.app_context():
        processar_publicacoes_djerj()
