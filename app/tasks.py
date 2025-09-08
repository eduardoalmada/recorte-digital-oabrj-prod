from celery import current_app as celery
from app import create_app
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_flask_app():
    """Retorna instância única da app Flask com contexto"""
    app = create_app()
    app.app_context().push()
    return app

@celery.task(
    name='app.tasks.tarefa_buscar_publicacoes',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300
)
def tarefa_buscar_publicacoes(self):
    """Task principal - ChromeDriver criado DENTRO da task"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa de busca de publicações...")
            
            # ✅ CHROME DRIVER CRIADO AQUI MESMO (SUA SOLUÇÃO)
            from app.scrapers.djen.djen_client import DJENClient
            client = DJENClient()  # ✅ Criado na task!
            
            # ✅ USA SEU DJENScraper MAS PASSANDO O CLIENT
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper(client)  # ✅ Client injetado!
            
            resultado_djen = scraper.executar()
            
            logger.info(f"✅ DJEN - {resultado_djen['total_publicacoes']} publicações encontradas")
            
            return {
                'status': 'success', 
                'message': 'Tarefas concluídas',
                'resultado_djen': resultado_djen,
            }
            
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de scraping: {e}")
        raise self.retry(exc=e, countdown=300)
    finally:
        # ✅ GARANTE FECHAMENTO (mesmo com erro)
        if 'client' in locals():
            try:
                client.close()
            except:
                pass
