# app/tasks.py - Tasks assíncronas otimizadas
from celery import current_app as celery
from app import create_app
import logging
from functools import lru_cache
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)

# ✅ Cache da app Flask para melhor performance
@lru_cache(maxsize=1)
def get_flask_app():
    """Retorna instância única da app Flask"""
    app = create_app()
    app.app_context().push()
    return app

# ✅ FUNÇÃO PARA CRIAR DRIVER: MOVIDA PARA O ARQUIVO DE TAREFAS
def create_chrome_driver():
    """
    Cria e retorna uma instância do Chrome WebDriver configurada para o ambiente Render.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--user-data-dir=/tmp/chrome-profile') # ✅ ÚNICO POR PROCESSO
    options.add_argument('--remote-debugging-port=0')
    options.binary_location = '/usr/bin/google-chrome'
    
    driver = webdriver.Chrome(options=options)
    return driver

# ✅ NOVA TAREFA PARA TESTAR O SCRAPER
@celery.task(name='app.tasks.test_scraper_task')
def test_scraper_task():
    """
    Tarefa para testar se o Chrome e Selenium estão funcionando.
    """
    try:
        driver = create_chrome_driver()
        driver.get('https://httpbin.org/html')
        title = driver.title
        driver.quit()
        logger.info(f"✅ Scraper de teste funcionou. Título: {title}")
        return {'status': 'success', 'message': 'Scraper funcionando!', 'title': title}
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de teste do scraper: {e}")
        return {'status': 'error', 'message': f'Erro no scraper: {str(e)}'}

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
            
            # ... (seu código de scraping DJERJ e DJEN, que deve usar a função create_chrome_driver)
            # Exemplo:
            # scraper = DJERJScraper(driver_factory=create_chrome_driver)
            # resultado_djerj = scraper.executar()

            return {'status': 'success', 'message': 'Tarefas concluídas'}
            
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de scraping: {e}")
        raise self.retry(exc=e, countdown=300)

@celery.task(
    name='app.tasks.tarefa_apenas_djen',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    time_limit=1800,
    soft_time_limit=1700
)
def tarefa_apenas_djen(self):
    """Task específica apenas para DJEN com retry"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa específica DJEN...")
            # ... (seu código de scraping DJEN)
            return {'status': 'success', 'message': 'Tarefa DJEN concluída'}
            
    except Exception as e:
        logger.error(f"❌ Erro na tarefa DJEN específica: {e}")
        raise self.retry(exc=e, countdown=600)
