# app/scrapers/djen/djen_client.py - VERSÃO COM SELENIUM
import logging
from datetime import date
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

logger = logging.getLogger(__name__)

class DJENClient:
    BASE_URL = "https://comunica.pje.jus.br"
    
    def __init__(self):
        self.driver = None
    
    def _inicializar_driver(self):
        """Inicializa o WebDriver do Selenium"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar driver: {e}")
            return False
    
    def buscar_publicacoes_por_data(self, data: date) -> List[Dict]:
        """Busca publicações usando Selenium (como no DJERJ)"""
        if not self.driver and not self._inicializar_driver():
            return []
        
        try:
            url = f"{self.BASE_URL}/consulta?dataDisponibilizacaoInicio={data.strftime('%Y-%m-%d')}&dataDisponibilizacaoFim={data.strftime('%Y-%m-%d')}"
            
            logger.info(f"🌐 Acessando DJEN: {url}")
            self.driver.get(url)
            
            # Aguarda carregamento
            time.sleep(3)
            
            # Tira screenshot para debug
            self.driver.save_screenshot("/tmp/djen_screenshot.png")
            logger.info("📸 Screenshot salva em /tmp/djen_screenshot.png")
            
            # Extrai o HTML da página
            html = self.driver.page_source
            
            return self._parse_resultados(html, data)
            
        except Exception as e:
            logger.error(f"Erro no Selenium DJEN: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _parse_resultados(self, html: str, data: date) -> List[Dict]:
        """Analisa os resultados (implementação simplificada inicial)"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        resultados = []
        
        # DEBUG: Salva o HTML para análise
        with open('/tmp/djen_html.html', 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info("📄 HTML salvo em /tmp/djen_html.html")
        
        # Aqui vamos implementar a lógica de parsing
        # Por enquanto, retorna lista vazia para testar conexão
        return resultados
