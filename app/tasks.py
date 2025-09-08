# app/tasks.py
from celery import current_app as celery
from app import create_app
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_flask_app():
    app = create_app()
    app.app_context().push()
    return app

@celery.task(
    name='app.tasks.tarefa_buscar_publicacoes',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300,
    # ✅ LIMITE DE CONCORRÊNCIA PARA EVITAR SOBRECARGA
    rate_limit='1/m'  # Máximo 1 task por minuto
)
def tarefa_buscar_publicacoes(self):
    """Task principal com proteção contra sobrecarga"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa de busca de publicações...")
            
            # ✅ MONITORAR MEMÓRIA ANTES DE CRIAR DRIVER
            import psutil
            memoria = psutil.virtual_memory()
            if memoria.percent > 80:
                logger.warning(f"⚠️ Memória alta ({memoria.percent}%), adiando task...")
                raise self.retry(countdown=300)  # Retry em 5min
            
            from app.scrapers.djen.djen_client import DJENClient
            client = DJENClient()  # ✅ Criado na task!
            
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper(client=client)
            
            resultado_djen = scraper.executar()
            
            logger.info(f"✅ DJEN - {resultado_djen['total_publicacoes']} publicações")
            
            return {
                'status': 'success', 
                'message': 'Tarefas concluídas',
                'resultado_djen': resultado_djen,
            }
            
    except MemoryError as e:
        logger.warning(f"🛑 Memória insuficiente: {e}, retry em 5min")
        raise self.retry(exc=e, countdown=300)
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de scraping: {e}")
        raise self.retry(exc=e, countdown=300)
    finally:
        if 'client' in locals():
            try:
                client.close()
                logger.info("✅ ChromeDriver fechado com sucesso")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao fechar client: {e}")
