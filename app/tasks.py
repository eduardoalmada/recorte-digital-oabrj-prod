# app/tasks.py - Tasks assíncronas otimizadas
from celery import current_app as celery
from app import create_app
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# ✅ Cache da app Flask para melhor performance
@lru_cache(maxsize=1)
def get_flask_app():
    """Retorna instância única da app Flask"""
    app = create_app()
    app.app_context().push()  # Já faz push do context
    return app

@celery.task(
    name='app.tasks.tarefa_buscar_publicacoes',
    bind=True,  # ✅ Permite acesso à task instance
    max_retries=3,  # ✅ Retry automático
    default_retry_delay=300,  # 5min entre retries
    time_limit=3600,
    soft_time_limit=3300
)
def tarefa_buscar_publicacoes(self):
    """Task principal para buscar publicações com retry automático"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa de busca de publicações...")
            
            # Primeiro executa DJERJ
            from app.scrapers.scraper_completo_djerj import executar_scraper_completo
            resultado_djerj = executar_scraper_completo()
            logger.info(f"✅ DJERJ completo: {resultado_djerj}")
            
            # Depois tenta DJEN
            resultado_djen = {'erro': 'não executado'}
            try:
                from app.scrapers.djen.djen_scraper import DJENScraper
                scraper_djen = DJENScraper()
                resultado_djen = scraper_djen.executar()
                logger.info(f"✅ DJEN executado: {resultado_djen}")
            except Exception as e:
                logger.error(f"❌ DJEN falhou: {e}")
                resultado_djen = {'erro': str(e)}
            
            return {
                'djerj': resultado_djerj,
                'djen': resultado_djen,
                'task_id': self.request.id
            }
            
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de scraping: {e}")
        # ✅ Retry automático para falhas
        raise self.retry(exc=e, countdown=300)

@celery.task(
    name='app.tasks.tarefa_apenas_djen',
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10min para DJEN
    time_limit=1800,  # 30min para DJEN
    soft_time_limit=1700
)
def tarefa_apenas_djen(self):
    """Task específica apenas para DJEN com retry"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa específica DJEN...")
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper()
            resultado = scraper.executar()
            logger.info(f"✅ DJEN específico completo: {resultado}")
            return resultado
            
    except Exception as e:
        logger.error(f"❌ Erro na tarefa DJEN específica: {e}")
        raise self.retry(exc=e, countdown=600)
