# app/scrapers/djen/djen_client.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tempfile
import time
import logging
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

class DJENClient:
    def __init__(self):
        options = Options()
        
        # ✅ HEADLESS MODERNO (ÚNICA ALTERAÇÃO NECESSÁRIA)
        options.add_argument('--headless=new')  # ✅ MUDANÇA AQUI
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=0')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')  # ✅ ADICIONAR
        
        # ✅ DIRETÓRIOS TEMPORÁRIOS ÚNICOS (SEU CÓDIGO JÁ ESTÁ PERFEITO)
        self.temp_user_dir = tempfile.mkdtemp(prefix='chrome-djen-')
        self.temp_cache_dir = tempfile.mkdtemp(prefix='chrome-cache-')
        
        options.add_argument(f'--user-data-dir={self.temp_user_dir}')
        options.add_argument(f'--disk-cache-dir={self.temp_cache_dir}')
        
        # ✅ EXECUTÁVEL CORRETO (JÁ ESTÁ CERTO)
        service = Service(executable_path='/usr/local/bin/chromedriver')
        
        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)
            self.BASE_URL = "https://comunica.pje.jus.br"
            logger.info("✅ ChromeDriver iniciado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Falha ao iniciar ChromeDriver: {e}")
            # Limpeza mesmo em caso de erro
            self._cleanup_temp_dirs()
            raise
    
    def buscar_publicacoes_por_data(self, data_ref):
        """Mantenha SEU código aqui - já está bom!"""
        # ... TODO SEU CÓDIGO DE NAVEGAÇÃO ...
        return []  # Seu código real
    
    def close(self):
        """Mantenha SEU código de limpeza - já está perfeito!"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass
        finally:
            self._cleanup_temp_dirs()
    
    def _cleanup_temp_dirs(self):
        """Limpeza dos diretórios temporários"""
        try:
            shutil.rmtree(self.temp_user_dir, ignore_errors=True)
        except:
            pass
        try:
            shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        except:
            pass
