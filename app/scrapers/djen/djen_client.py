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

# ✅ DECORATOR PARA RETRY AUTOMÁTICO
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
        # ✅ MONITORAMENTO INICIAL (APENAS WARNING, NÃO ERRO)
        self.memoria_inicial = psutil.virtual_memory()
        if self.memoria_inicial.percent > 85:
            logger.warning(f"🚨 Memória inicial alta: {self.memoria_inicial.percent}% - Continuando com cautela")
        
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')  # ✅ MAIS ESTABILIDADE
        options.add_argument('--remote-debugging-port=9222')   # ✅ PORTA FIXA
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        
        # ✅ OTIMIZAÇÕES DE PERFORMANCE
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # ✅ DIRETÓRIOS TEMPORÁRIOS ÚNICOS (COM TIMESTAMP)
        self.temp_user_dir = tempfile.mkdtemp(prefix=f'chrome-djen-{int(time.time())}-')
        self.temp_cache_dir = tempfile.mkdtemp(prefix=f'chrome-cache-{int(time.time())}-')
        options.add_argument(f'--user-data-dir={self.temp_user_dir}')
        options.add_argument(f'--disk-cache-dir={self.temp_cache_dir}')
        
        self.service = Service(executable_path='/usr/local/bin/chromedriver')
        
        try:
            self.driver = webdriver.Chrome(service=self.service, options=options)
            self.driver.implicitly_wait(10)
            self.BASE_URL = "https://comunica.pje.jus.br"
            
            logger.info(f"🚀 ChromeDriver iniciado | Memória: {self.memoria_inicial.percent}% | Temp dir: {self.temp_user_dir}")
            
        except Exception as e:
            self._cleanup_temp_dirs()
            raise
    
    # ✅ WAIT PERSONALIZADO COM TIMEOUT CONFIGURÁVEL
    def _wait_for_element(self, by, value, timeout=10, poll_frequency=0.5):
        """Wait personalizado para elementos com timeout fino"""
        try:
            return WebDriverWait(
                self.driver, 
                timeout=timeout,
                poll_frequency=poll_frequency
            ).until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            logger.warning(f"⏰ Timeout esperando elemento: {value}")
            raise
    
    # ✅ RETRY AUTOMÁTICO PARA BUSCA DE ELEMENTOS
    @retry_on_failure(max_retries=2, delay=1)
    def _find_element_with_retry(self, by, value):
        """Busca elemento com retry automático"""
        return self.driver.find_element(by, value)
    
    def buscar_publicacoes_por_data(self, data_ref):
        """
        Busca publicações do DJEN para uma data específica.
        Retorna: lista de dicionários com publicações
        """
        publicacoes = []
        
        try:
            logger.info(f"🌐 Navegando para DJEN - Data: {data_ref}")
            data_formatada = data_ref.strftime('%d/%m/%Y')
            
            # ✅ NAVEGAÇÃO COM TIMEOUT FINO
            self.driver.get(self.BASE_URL)
            self._wait_for_element(By.TAG_NAME, "body", timeout=15)
            
            # ✅ SUBSTITUI time.sleep() POR WAITS ESPECÍFICOS
            try:
                diario_link = self._wait_for_element(
                    By.LINK_TEXT, "Diário de Justiça", timeout=8
                )
                diario_link.click()
                self._wait_for_element(By.TAG_NAME, "body", timeout=5)
                
            except TimeoutException:
                logger.warning("Diário de Justiça não encontrado, continuando...")
            
            # ✅ PREENCHIMENTO COM RETRY
            try:
                campo_data = self._find_element_with_retry(By.NAME, "data")
                campo_data.clear()
                campo_data.send_keys(data_formatada)
                
                botao_buscar = self._find_element_with_retry(
                    By.XPATH, "//button[contains(text(), 'Buscar')]"
                )
                botao_buscar.click()
                
                # ✅ WAIT PARA RESULTADOS CARREGAREM
                self._wait_for_element(
                    By.CLASS_NAME, "publicacao", timeout=10
                )
                
                publicacoes_elements = self.driver.find_elements(By.CLASS_NAME, "publicacao")
                
                for pub_element in publicacoes_elements:
                    try:
                        publicacao = {
                            'texto': pub_element.text,
                            'data': data_ref.isoformat(),
                            'url': self.driver.current_url,
                            'timestamp': datetime.now().isoformat()
                        }
                        publicacoes.append(publicacao)
                    except Exception as e:
                        logger.warning(f"Erro ao extrair publicação: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Erro durante busca: {e}")
                publicacoes.append({
                    'texto': f"Erro: {str(e)}",
                    'data': data_ref.isoformat(),
                    'url': self.driver.current_url,
                    'error': True
                })
            
            logger.info(f"✅ {len(publicacoes)} publicações encontradas")
            
        except Exception as e:
            logger.error(f"❌ Erro geral: {e}")
            publicacoes.append({
                'texto': f"Erro geral: {str(e)}",
                'data': data_ref.isoformat(),
                'url': self.driver.current_url,
                'error': True
            })
        
        return publicacoes
    
    def close(self):
        """Fecha o driver com monitoramento de recursos"""
        try:
            if hasattr(self, 'driver'):
                # ✅ MONITORAMENTO FINAL DE RECURSOS
                memoria_final = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent()
                
                logger.info(
                    f"📊 Recursos finais | "
                    f"Memória: {memoria_final.percent}% (+{memoria_final.percent - self.memoria_inicial.percent:.1f}%) | "
                    f"CPU: {cpu_percent}%"
                )
                
                # ✅ ALERTA SE CONSUMO ELEVADO
                if memoria_final.percent > 90:
                    logger.warning("🚨 ALTA UTILIZAÇÃO DE MEMÓRIA")
                if cpu_percent > 85:
                    logger.warning("🚨 ALTA UTILIZAÇÃO DE CPU")
                
                # ✅ FECHAMENTO GARANTIDO (DRIVER + SERVICE)
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
            shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
            logger.debug(f"🧹 Diretórios temporários limpos: {self.temp_user_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Erro na limpeza: {e}")
