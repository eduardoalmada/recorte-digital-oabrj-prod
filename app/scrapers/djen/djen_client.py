# app/scrapers/djen/djen_client.py - VERSÃO CORRIGIDA
import logging
from datetime import date
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

logger = logging.getLogger(__name__)

class DJENClient:
    BASE_URL = "https://comunica.pje.jus.br"
    
    def __init__(self):
        self.driver = None
    
    def _inicializar_driver(self):
        """Inicializa o WebDriver com configurações otimizadas para Render"""
        try:
            chrome_options = Options()
            
            # Configurações ESSENCIAIS para Render
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--remote-debugging-port=0")
            chrome_options.add_argument("--disable-setuid-sandbox")
            
            # Configurações de performance
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--ignore-certificate-errors")
            
            # User agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Configurações experimentais
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # IMPORTANTE: Configurações para evitar timeout
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument("--single-process")
            
            # Inicializa o driver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Timeouts reduzidos para Render
            self.driver.set_page_load_timeout(45)
            self.driver.implicitly_wait(10)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar driver: {e}")
            return False
    
    def buscar_publicacoes_por_data(self, data: date) -> List[Dict]:
        """Busca publicações com tratamento robusto de erros"""
        if not self._inicializar_driver():
            return []
        
        try:
            url = f"{self.BASE_URL}/consulta?dataDisponibilizacaoInicio={data.strftime('%Y-%m-%d')}&dataDisponibilizacaoFim={data.strftime('%Y-%m-%d')}"
            
            logger.info(f"🌐 Acessando DJEN: {url}")
            
            # Tentativa com timeout controlado
            self.driver.get(url)
            
            # Aguarda de forma inteligente
            time.sleep(2)  # Espera inicial
            
            # Verifica se carregou
            if "comunica" in self.driver.current_url:
                logger.info("✅ Página carregada com sucesso")
                
                # Tira screenshot para debug
                try:
                    self.driver.save_screenshot("/tmp/djen_screenshot.png")
                    logger.info("📸 Screenshot salva")
                except:
                    pass
                
                # Extrai HTML
                html = self.driver.page_source
                
                # DEBUG: Salva HTML
                with open('/tmp/djen_html.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info("📄 HTML salvo")
                
                return self._parse_resultados(html, data)
            else:
                logger.error("❌ Página não carregou corretamente")
                return []
                
        except Exception as e:
            logger.error(f"Erro no Selenium DJEN: {e}")
            return []
        finally:
            self._fechar_driver()
    
    def _fechar_driver(self):
        """Fecha o driver de forma segura"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
        finally:
            self.driver = None
    
    def _parse_resultados(self, html: str, data: date) -> List[Dict]:
        """Placeholder - foca primeiro em conectar, depois implementamos parsing"""
        # Por enquanto retorna lista vazia - o importante é conectar
        return []

    def teste_conexao_simples(self):
        """Teste simplificado só para verificar se consegue conectar"""
        try:
            if not self._inicializar_driver():
                return False
                
            self.driver.get("https://www.google.com")
            time.sleep(2)
            
            success = "google" in self.driver.current_url.lower()
            logger.info(f"✅ Teste de conexão: {'Sucesso' if success else 'Falha'}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erro teste conexão: {e}")
            return False
        finally:
            self._fechar_driver()
