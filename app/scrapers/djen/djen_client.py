# app/scrapers/djen/djen_client.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import tempfile
import time
import logging
from datetime import datetime
import shutil
import psutil
from functools import wraps
import retry

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"❌ Falha após {max_retries} tentativas: {e}")
                        raise
                    logger.warning(f"⚠️ Tentativa {retries}/{max_retries} falhou: {e}")
                    time.sleep(delay * (backoff ** (retries - 1)))
            return func(*args, **kwargs)
        return wrapper
    return decorator

class DJENClient:
    def __init__(self):
        # ✅ MONITORAMENTO INICIAL
        self.memoria_inicial = psutil.virtual_memory()
        if self.memoria_inicial.percent > 85:
            logger.warning(f"🚨 Memória inicial alta: {self.memoria_inicial.percent}% - Continuando com cautela")
        
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        
        # ✅ OTIMIZAÇÕES DE PERFORMANCE
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # ✅ SOLUÇÃO DEFINITIVA: DIRETÓRIO TEMPORÁRIO ÚNICO
        self.temp_user_dir = tempfile.mkdtemp(prefix=f'chrome-djen-{int(time.time())}-')
        options.add_argument(f'--user-data-dir={self.temp_user_dir}')
        options.add_argument('--incognito')
        
        self.service = Service(executable_path='/usr/local/bin/chromedriver')
        
        try:
            self.driver = webdriver.Chrome(service=self.service, options=options)
            self.driver.implicitly_wait(10)
            self.BASE_URL = "https://comunica.pje.jus.br"
            
            logger.info(f"🚀 ChromeDriver iniciado | Memória: {self.memoria_inicial.percent}% | Temp dir: {self.temp_user_dir}")
            
        except Exception as e:
            self._cleanup_temp_dirs()
            raise
    
    # ... (resto dos métodos permanece igual)

    def close(self):
        """Fecha o driver com monitoramento de recursos"""
        try:
            if hasattr(self, 'driver'):
                memoria_final = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent()
                
                logger.info(f"📊 Recursos finais | Memória: {memoria_final.percent}% | CPU: {cpu_percent}%")
                
                self.driver.quit()
                if hasattr(self, 'service'):
                    self.service.stop()
                logger.info("✅ ChromeDriver e Service fechados")
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao fechar driver: {e}")
        finally:
            self._cleanup_temp_dirs()
    
    def _cleanup_temp_dirs(self):
        """Limpeza dos diretórios temporários"""
        try:
            shutil.rmtree(self.temp_user_dir, ignore_errors=True)
            logger.debug(f"🧹 Diretório temporário limpo: {self.temp_user_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Erro na limpeza: {e}")
