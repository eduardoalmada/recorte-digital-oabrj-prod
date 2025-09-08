# ✅ VERSÃO CORRIGIDA (Selenium 4.x) - COM DIRETÓRIOS TEMPORÁRIOS ÚNICOS
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

logger = logging.getLogger(__name__)

class DJENClient:
    def __init__(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--remote-debugging-port=0')
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # ✅ DIRETÓRIOS TEMPORÁRIOS ÚNICOS (evita conflito)
        self.temp_user_dir = tempfile.mkdtemp(prefix='chrome-djen-')
        self.temp_cache_dir = tempfile.mkdtemp(prefix='chrome-cache-')
        
        options.add_argument(f'--user-data-dir={self.temp_user_dir}')
        options.add_argument(f'--disk-cache-dir={self.temp_cache_dir}')
        
        # ✅ FORMA CORRETA (Selenium 4+)
        service = Service(executable_path='/usr/local/bin/chromedriver')
        self.driver = webdriver.Chrome(service=service, options=options)
        
        self.BASE_URL = "https://comunica.pje.jus.br"
        self.driver.implicitly_wait(10)
    
    def buscar_publicacoes_por_data(self, data_ref):
        """
        Busca publicações do DJEN para uma data específica.
        Retorna: lista de dicionários com publicações
        """
        publicacoes = []
        
        try:
            logger.info(f"🌐 Navegando para o DJEN - Data: {data_ref}")
            
            # Formata a data para o padrão DD/MM/AAAA
            data_formatada = data_ref.strftime('%d/%m/%Y')
            
            # Navega para a página principal
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            
            # Aqui você precisa implementar a navegação real do DJEN
            # Exemplo genérico (adaptar para o site real):
            
            # 1. Clicar em "Diário de Justiça"
            try:
                diario_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Diário de Justiça"))
                )
                diario_link.click()
                time.sleep(2)
            except:
                logger.warning("Link 'Diário de Justiça' não encontrado")
            
            # 2. Preencher data e buscar
            try:
                # Localizar campo de data (adaptar seletor conforme site)
                campo_data = self.driver.find_element(By.NAME, "data")
                campo_data.clear()
                campo_data.send_keys(data_formatada)
                time.sleep(1)
                
                # Clicar em buscar (adaptar seletor conforme site)
                botao_buscar = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar')]")
                botao_buscar.click()
                time.sleep(3)
                
                # Extrair publicações (adaptar seletores conforme site)
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
                logger.error(f"Erro durante a busca: {e}")
                # Fallback: captura o HTML da página para análise
                publicacoes.append({
                    'texto': f"Erro na busca: {str(e)} - Página: {self.driver.current_url}",
                    'data': data_ref.isoformat(),
                    'url': self.driver.current_url,
                    'error': True
                })
            
            logger.info(f"✅ Encontradas {len(publicacoes)} publicações")
            
        except Exception as e:
            logger.error(f"❌ Erro geral no DJENClient: {e}")
            publicacoes.append({
                'texto': f"Erro geral: {str(e)}",
                'data': data_ref.isoformat(),
                'url': self.driver.current_url if hasattr(self, 'driver') else 'N/A',
                'error': True
            })
        
        return publicacoes
    
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
