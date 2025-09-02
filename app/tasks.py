from app.celery_worker import celery
from app import create_app
import logging

logger = logging.getLogger(__name__)

@celery.task
def tarefa_buscar_publicacoes():
    """Task principal que já existe - manter compatibilidade"""
    app = create_app()
    
    with app.app_context():
        try:
            # Primeiro executa DJERJ (existente)
            from app.scrapers.scraper_completo_djerj import executar_scraper_completo
            resultado_djerj = executar_scraper_completo()
            
            # Depois tenta DJEN (novo)
            try:
                from app.scrapers.djen.djen_scraper import DJENScraper
                scraper_djen = DJENScraper()
                resultado_djen = scraper_djen.executar()
                logger.info(f"DJEN executado: {resultado_djen}")
            except Exception as e:
                logger.error(f"DJEN falhou: {e}")
                resultado_djen = {'erro': str(e)}
            
            return {
                'djerj': resultado_djerj,
                'djen': resultado_djen
            }
            
        except Exception as e:
            logger.error(f"Erro na tarefa de scraping: {e}")
            return {'erro': str(e)}

@celery.task
def tarefa_apenas_djen():
    """Nova task específica para DJEN"""
    app = create_app()
    
    with app.app_context():
        try:
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper()
            return scraper.executar()
        except Exception as e:
            logger.error(f"Erro na tarefa DJEN: {e}")
            return {'erro': str(e)}
