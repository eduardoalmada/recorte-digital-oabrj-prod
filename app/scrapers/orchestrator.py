import logging
from datetime import datetime
from app import create_app

logger = logging.getLogger(__name__)

def executar_scraping_completo():
    """Orquestra scraping DJERJ + DJEN"""
    app = create_app()
    
    with app.app_context():
        inicio = datetime.now()
        logger.info("🚀 INICIANDO SCRAPING COMPLETO (DJERJ + DJEN)")
        
        # Executa DJERJ (seu código existente)
        from app.scrapers.djerj.scraper_completo_djerj import executar_scraper_completo
        resultado_djerj = executar_scraper_completo()
        
        # Executa DJEN (novo)
        try:
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper_djen = DJENScraper()
            resultado_djen = scraper_djen.executar()
        except Exception as e:
            logger.error(f"❌ DJEN não executado: {e}")
            resultado_djen = {'erro': str(e)}
        
        # Log de resultados
        duracao = (datetime.now() - inicio).total_seconds()
        logger.info(f"✅ SCRAPING CONCLUÍDO - {duracao:.2f}s")
        
        return {
            'djerj': resultado_djerj,
            'djen': resultado_djen
        }
