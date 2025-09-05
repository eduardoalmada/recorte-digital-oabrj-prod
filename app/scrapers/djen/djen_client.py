# ✅ VERSÃO CORRIGIDA (Selenium 4.x)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service  # ✅ NOVO
import os

class DJENClient:
    def __init__(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument(f'--user-data-dir=/tmp/chrome-profile-djen-{os.getpid()}')
        options.add_argument('--remote-debugging-port=0')
        
        # ✅ FORMA CORRETA (Selenium 4+)
        service = Service(executable_path='/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        
        self.BASE_URL = "https://comunica.pje.jus.br"
