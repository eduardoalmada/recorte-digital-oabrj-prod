from celery import shared_task
from app import create_app, db
from app.scrapers import scraper_djerj_selenium

@shared_task
def tarefa_buscar_publicacoes():
    app = create_app()
    with app.app_context():
        try:
            scraper_djerj_selenium.executar_scraper()
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na tarefa Celery: {e}")
        finally:
            db.session.remove()
