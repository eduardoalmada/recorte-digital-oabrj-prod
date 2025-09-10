from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import tempfile
import shutil
import logging
import os

logger = logging.getLogger(__name__)

def get_chromedriver_path():
    """Retorna o caminho correto do chromedriver"""
    possible_paths = [
        '/usr/local/bin/chromedriver',
        '/usr/bin/chromedriver', 
        '/app/chromedriver',
        os.environ.get('CHROMEDRIVER_PATH', '')
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path):
            logger.info(f"✅ Chromedriver encontrado em: {path}")
            return path
    
    # Fallback: usa o do sistema PATH
    logger.warning("⚠️ Chromedriver não encontrado, usando PATH do sistema")
    return 'chromedriver'

def create_chrome_driver():
    """Cria ChromeDriver com perfil temporário único"""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--remote-debugging-port=0')
    
    # ✅ DIRETÓRIO TEMPORÁRIO ÚNICO
    user_data_dir = tempfile.mkdtemp(prefix='chrome-profile-')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    
    # ✅ CAMINHO CORRETO DO CHROMEDRIVER
    chromedriver_path = get_chromedriver_path()
    service = Service(executable_path=chromedriver_path)
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver._temp_dir = user_data_dir  # Para cleanup posterior
        logger.info(f"🚀 ChromeDriver iniciado | Temp dir: {user_data_dir}")
        return driver
    except Exception as e:
        # Limpeza em caso de erro
        shutil.rmtree(user_data_dir, ignore_errors=True)
        raise

def cleanup_chrome_driver(driver):
    """Fecha driver e limpa diretório temporário"""
    if not driver:
        return
        
    try:
        if hasattr(driver, 'quit'):
            driver.quit()
            logger.info("✅ ChromeDriver fechado")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao fechar driver: {e}")
    finally:
        if hasattr(driver, '_temp_dir'):
            try:
                shutil.rmtree(driver._temp_dir, ignore_errors=True)
                logger.debug(f"🧹 Diretório limpo: {driver._temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao limpar diretório: {e}")
