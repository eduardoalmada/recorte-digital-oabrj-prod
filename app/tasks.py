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
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa de busca de publicações...")
            
            # ✅ SCRAPER DJEN - IMPLEMENTAÇÃO REAL
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper()
            resultado_djen = scraper.executar()
            
            logger.info(f"✅ DJEN - {resultado_djen['total_publicacoes']} publicações encontradas")
            
            # ✅ SCRAPER DJERJ (se tiver)
            # from app.scrapers.djerj.scraper_completo_djerj import DJERJScraper
            # scraper_djerj = DJERJScraper()
            # resultado_djerj = scraper_djerj.executar()
            
            return {
                'status': 'success', 
                'message': 'Tarefas concluídas',
                'resultado_djen': resultado_djen,
                # 'resultado_djerj': resultado_djerj  # descomente quando implementar
            }
            
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de scraping: {e}")
        raise self.retry(exc=e, countdown=300)
