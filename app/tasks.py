from celery import current_app as celery
from app import create_app
import logging
from functools import lru_cache  # ✅ Import necessário para o cache

logger = logging.getLogger(__name__)

# ✅ ADICIONE ESTA FUNÇÃO (ela estava faltando)
@lru_cache(maxsize=1)
def get_flask_app():
    """Retorna instância única da app Flask com contexto"""
    app = create_app()
    app.app_context().push()  # ✅ Cria e ativa o contexto
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
    """Task principal para buscar publicações com retry automático"""
    app = get_flask_app()  # ✅ AGORA ESTA FUNÇÃO EXISTE
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa de busca de publicações...")
            
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper()
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
