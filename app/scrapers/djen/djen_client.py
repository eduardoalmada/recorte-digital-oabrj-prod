# ✅ VERSÃO CORRIGIDA (Selenium 4.x) - COM DIRETÓRIOS TEMPORÁRIOS ÚNICOS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import tempfile
import os

class DJENClient:
    def __init__(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=0')
        
        # ✅ DIRETÓRIOS TEMPORÁRIOS ÚNICOS (evita conflito)
        self.temp_user_dir = tempfile.mkdtemp(prefix='chrome-djen-')
        self.temp_cache_dir = tempfile.mkdtemp(prefix='chrome-cache-')
        
        options.add_argument(f'--user-data-dir={self.temp_user_dir}')
        options.add_argument(f'--disk-cache-dir={self.temp_cache_dir}')
        
        # ✅ FORMA CORRETA (Selenium 4+)
        service = Service(executable_path='/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        
        self.BASE_URL = "https://comunica.pje.jus.br"
    
    def close(self):
        """Fecha o driver e limpa diretórios temporários"""
        try:
            self.driver.quit()
        except:
            pass
        
        # Limpeza dos diretórios temporários
        import shutil
        try:
            shutil.rmtree(self.temp_user_dir, ignore_errors=True)
        except:
            pass
        try:
            shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        except:
            pass
