# app/scrapers/djen/djen_client.py - VERSÃO OTIMIZADA
import logging
from datetime import date
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import os
import subprocess

logger = logging.getLogger(__name__)

class DJENClient:
    BASE_URL = "https://comunica.pje.jus.br"
    
    def __init__(self):
        self.driver = None
        self._verificar_dependencias()
    
    def _verificar_dependencias(self):
        """Verifica se Chrome e ChromeDriver estão instalados corretamente"""
        try:
            # Verifica Chrome
            chrome_version = subprocess.check_output(
                ['google-chrome', '--version'], 
                stderr=subprocess.STDOUT, 
                text=True,
                timeout=10
            )
            logger.info(f"✅ Chrome detectado: {chrome_version.strip()}")
            
            # Verifica ChromeDriver
            driver_version = subprocess.check_output(
                ['chromedriver', '--version'],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10
            )
            logger.info(f"✅ ChromeDriver detectado: {driver_version.strip()}")
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"❌ Erro na verificação de dependências: {e}")
            raise RuntimeError("Chrome ou ChromeDriver não estão instalados corretamente")
    
    def _inicializar_driver(self):
        """Inicializa o WebDriver com configurações otimizadas para Render"""
        try:
            chrome_options = Options()
            
            # 🔧 CONFIGURAÇÕES CRÍTICAS PARA RENDER
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-setuid-sandbox")
            
            # 🚀 CONFIGURAÇÕES DE PERFORMANCE
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            
            # 👤 USER AGENT E IDENTIFICAÇÃO
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # ⚡ CONFIGURAÇÕES EXPERIMENTAIS
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 🛡️ CONFIGURAÇÕES DE SEGURANÇA
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-zygote")
            chrome_options.add_argument("--single-process")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            
            # 📁 CONFIGURAÇÕES DE MEMÓRIA
            chrome_options.add_argument("--memory-pressure-off")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            
            # 🌐 CONFIGURAÇÕES DE REDE
            chrome_options.add_argument("--disable-domain-reliability")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--disable-client-side-phishing-detection")
            
            logger.info("🔄 Inicializando ChromeDriver...")
            
            # 🚀 INICIALIZAÇÃO COM TIMEOUT CONTROLADO
            try:
                self.driver = webdriver.Chrome(
                    options=chrome_options,
                    service_args=['--verbose', '--log-path=/tmp/chromedriver.log']
                )
            except WebDriverException as e:
                logger.warning(f"Primeira tentativa falhou, tentando abordagem alternativa: {e}")
                # Tentativa alternativa
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # ⏰ TIMEOUTS OTIMIZADOS
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(20)
            self.driver.implicitly_wait(5)
            
            logger.info("✅ ChromeDriver inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar driver: {e}")
            # Log adicional para debugging
            try:
                if os.path.exists('/tmp/chromedriver.log'):
                    with open('/tmp/chromedriver.log', 'r') as f:
                        log_content = f.read()
                    logger.error(f"ChromeDriver log: {log_content[-500:]}")
            except:
                pass
            return False
    
    def buscar_publicacoes_por_data(self, data: date) -> List[Dict]:
        """Busca publicações com tratamento robusto de erros"""
        if not self._inicializar_driver():
            return []
        
        try:
            url = f"{self.BASE_URL}/consulta?dataDisponibilizacaoInicio={data.strftime('%Y-%m-%d')}&dataDisponibilizacaoFim={data.strftime('%Y-%m-%d')}"
            
            logger.info(f"🌐 Acessando DJEN: {url}")
            
            # 🎯 TENTATIVA DE CARREGAMENTO COM TIMEOUT CONTROLADO
            try:
                self.driver.get(url)
                
                # ⏳ AGUARDA INTELIGENTE - Verifica elementos-chave
                wait = WebDriverWait(self.driver, 15)
                
                # Verifica se a página carregou completamente
                try:
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    logger.info("✅ Página carregada - body detectado")
                except TimeoutException:
                    logger.warning("⚠️  Timeout aguardando body, continuando mesmo assim")
                
                # Verifica se é a página correta
                current_url = self.driver.current_url
                if "comunica.pje.jus.br" in current_url:
                    logger.info(f"✅ Página carregada com sucesso: {current_url}")
                    
                    # 📸 DEBUG: Screenshot
                    try:
                        self.driver.save_screenshot("/tmp/djen_screenshot.png")
                        logger.info("📸 Screenshot salva em /tmp/djen_screenshot.png")
                    except Exception as screenshot_error:
                        logger.warning(f"⚠️  Erro ao salvar screenshot: {screenshot_error}")
                    
                    # 📄 DEBUG: HTML completo
                    try:
                        html = self.driver.page_source
                        with open('/tmp/djen_html.html', 'w', encoding='utf-8') as f:
                            f.write(html)
                        logger.info("📄 HTML salvo em /tmp/djen_html.html")
                        logger.info(f"📊 Tamanho do HTML: {len(html)} caracteres")
                        
                        return self._parse_resultados(html, data)
                        
                    except Exception as html_error:
                        logger.error(f"❌ Erro ao extrair HTML: {html_error}")
                        return []
                        
                else:
                    logger.error(f"❌ Redirecionamento inesperado: {current_url}")
                    return []
                    
            except TimeoutException:
                logger.error("❌ Timeout ao carregar a página")
                return []
            except Exception as navigation_error:
                logger.error(f"❌ Erro de navegação: {navigation_error}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erro no Selenium DJEN: {e}")
            return []
        finally:
            self._fechar_driver()
    
    def _fechar_driver(self):
        """Fecha o driver de forma segura"""
        try:
            if self.driver:
                logger.info("🔄 Fechando driver...")
                self.driver.quit()
                logger.info("✅ Driver fechado com sucesso")
        except Exception as e:
            logger.warning(f"⚠️  Erro ao fechar driver: {e}")
        finally:
            self.driver = None
    
    def _parse_resultados(self, html: str, data: date) -> List[Dict]:
        """Análise inicial do HTML - versão de debug"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 📊 ESTATÍSTICAS BÁSICAS PARA DEBUG
            title = soup.find('title')
            logger.info(f"📝 Título da página: {title.get_text() if title else 'N/A'}")
            
            forms = soup.find_all('form')
            tables = soup.find_all('table')
            links = soup.find_all('a')
            
            logger.info(f"📊 Estatísticas: {len(forms)} forms, {len(tables)} tables, {len(links)} links")
            
            # 🎯 PROCURA POR ELEMENTOS-CHAVE
            elementos_chave = ['publicacao', 'comunicacao', 'diario', 'processo', 'advogado']
            for elemento in elementos_chave:
                if elemento in html.lower():
                    logger.info(f"🔍 Encontrado termo-chave: {elemento}")
            
            # 📋 LISTA PRIMEIROS LINKS PARA DEBUG
            for i, link in enumerate(links[:5]):
                href = link.get('href', '')
                texto = link.get_text(strip=True)
                if href or texto:
                    logger.info(f"🔗 Link {i+1}: {texto} -> {href}")
            
            # 📍 PLACEHOLDER - IMPLEMENTAR PARSING REAL AQUI
            # Por enquanto retorna lista vazia para focar na conexão
            return []
            
        except Exception as e:
            logger.error(f"❌ Erro no parsing HTML: {e}")
            return []
    
    def teste_conexao_simples(self):
        """Teste simplificado só para verificar se consegue conectar"""
        try:
            if not self._inicializar_driver():
                return False
                
            logger.info("🧪 Testando conexão com Google...")
            self.driver.get("https://www.google.com")
            
            # Aguarda carga completa
            time.sleep(2)
            
            success = "google" in self.driver.current_url.lower()
            logger.info(f"✅ Teste de conexão: {'Sucesso' if success else 'Falha'}")
            
            if success:
                # Tenta interagir com a página
                try:
                    search_box = self.driver.find_element(By.NAME, "q")
                    logger.info("✅ Elemento de pesquisa encontrado - Selenium funcional")
                except:
                    logger.warning("⚠️  Elemento de pesquisa não encontrado, mas página carregada")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erro teste conexão: {e}")
            return False
        finally:
            self._fechar_driver()

    def health_check(self):
        """Verificação completa de saúde do sistema"""
        checks = {
            'chrome_installed': False,
            'chromedriver_installed': False,
            'selenium_import': False,
            'basic_connection': False
        }
        
        try:
            # Verifica Chrome
            try:
                subprocess.run(['google-chrome', '--version'], check=True, 
                              capture_output=True, timeout=5)
                checks['chrome_installed'] = True
            except:
                logger.error("❌ Chrome não está instalado")
                return checks
            
            # Verifica ChromeDriver
            try:
                subprocess.run(['chromedriver', '--version'], check=True,
                              capture_output=True, timeout=5)
                checks['chromedriver_installed'] = True
            except:
                logger.error("❌ ChromeDriver não está instalado")
                return checks
            
            # Verifica importação Selenium
            try:
                from selenium import webdriver
                checks['selenium_import'] = True
            except ImportError as e:
                logger.error(f"❌ Selenium não pode ser importado: {e}")
                return checks
            
            # Teste de conexão básica
            checks['basic_connection'] = self.teste_conexao_simples()
            
            return checks
            
        except Exception as e:
            logger.error(f"❌ Erro no health check: {e}")
            return checks
