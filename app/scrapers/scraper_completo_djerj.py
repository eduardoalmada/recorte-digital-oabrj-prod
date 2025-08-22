# app/scrapers/scraper_completo_djerj.py
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import re
from app import db
from app.models import DiarioOficial
from pdfminer.high_level import extract_text

def baixar_pdf_durante_sessao(data):
    """Baixa o PDF durante a sessão do Selenium para evitar expiração"""
    print(f'🔍 Buscando PDF para {data.strftime("%d/%m/%Y")}...')
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = f'https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime("%d/%m/%Y")}&caderno=E&pagina=-1'
        driver.get(url)
        
        # Esperar carregamento
        time.sleep(5)
        
        # Analisar iframes
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        
        for iframe in iframes:
            iframe_src = iframe.get_attribute('src') or ''
            
            # Se for o iframe do PDF, analisar seu conteúdo
            if 'pdf.aspx' in iframe_src:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(3)
                    
                    # Analisar o HTML do iframe
                    iframe_html = driver.page_source
                    
                    # Procurar por filenames no iframe
                    iframe_filenames = re.findall(r'filename=([^&"\']+)', iframe_html)
                    print(f'📝 Filenames encontrados: {iframe_filenames}')
                    
                    for filename in iframe_filenames:
                        # Corrigir filename se necessário
                        if filename.startswith('/consultadje/temp/'):
                            filename = filename.replace('/consultadje/temp/', '')
                        
                        # Construir URL correta
                        pdf_url = f'https://www3.tjrj.jus.br/consultadje/temp/{filename}'
                        print(f'🎯 URL do PDF: {pdf_url}')
                        
                        # **BAIXAR DURANTE A SESSÃO** - usar os cookies do Selenium
                        cookies = driver.get_cookies()
                        session = requests.Session()
                        
                        # Transferir cookies do Selenium para requests
                        for cookie in cookies:
                            session.cookies.set(cookie['name'], cookie['value'])
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': 'application/pdf, */*',
                            'Referer': driver.current_url
                        }
                        
                        # Baixar IMEDIATAMENTE
                        try:
                            response = session.get(pdf_url, headers=headers, timeout=15)
                            print(f'📊 Status: {response.status_code}, Tamanho: {len(response.content)}')
                            
                            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                                print('✅ PDF baixado com sucesso durante a sessão!')
                                driver.switch_to.default_content()
                                return response.content
                            else:
                                print('❌ Resposta não é um PDF válido')
                                # Debug: ver conteúdo da resposta
                                print(f'Primeiros bytes: {response.content[:100]}')
                                
                        except Exception as e:
                            print(f'❌ Erro ao baixar: {e}')
                    
                    driver.switch_to.default_content()
                    
                except Exception as e:
                    print(f'❌ Erro ao analisar iframe: {e}')
                    driver.switch_to.default_content()
        
        return None
            
    except Exception as e:
        print(f'❌ Erro durante a busca: {e}')
        return None
    finally:
        driver.quit()

def extrair_texto_pdf(caminho_pdf):
    """Extrai texto do PDF"""
    try:
        return extract_text(caminho_pdf)
    except Exception as e:
        print(f'❌ Erro ao extrair texto: {e}')
        return ""

def executar_scraper_djerj():
    hoje = datetime.now().date()
    
    print(f'📅 Verificando DJERJ de {hoje.strftime("%d/%m/%Y")}')
    
    # Verificar se já foi processado
    if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
        print(f'✅ DJERJ de {hoje.strftime("%d/%m/%Y")} já processado')
        return
    
    # Baixar PDF durante a sessão
    pdf_content = baixar_pdf_durante_sessao(hoje)
    
    if pdf_content:
        # Salvar temporariamente
        os.makedirs('temp', exist_ok=True)
        caminho_pdf = f'temp/diario_{hoje.strftime("%Y%m%d")}.pdf'
        
        with open(caminho_pdf, 'wb') as f:
            f.write(pdf_content)
        
        print(f'✅ PDF baixado com sucesso! Tamanho: {len(pdf_content)} bytes')
        
        # Extrair texto
        texto = extrair_texto_pdf(caminho_pdf)
        
        if texto and len(texto.strip()) > 100:
            # Verificar se contém o advogado
            if 'PEDRO JOSÉ CARDOSO DOS SANTOS' in texto:
                print('✅ Advogado encontrado no PDF!')
            else:
                print('🔍 Procurando por partes do nome...')
                if 'PEDRO' in texto and 'JOSÉ' in texto and 'CARDOSO' in texto:
                    print('✅ Partes do nome encontradas!')
            
            # Contar publicações
            total_publicacoes = texto.count('Advogado') + texto.count('ADVOGADO')
            
            novo_diario = DiarioOficial(
                data_publicacao=hoje,
                fonte='DJERJ',
                total_publicacoes=total_publicacoes,
                arquivo_pdf=caminho_pdf
            )
            
            db.session.add(novo_diario)
            db.session.commit()
            
            print(f'✅ Diário salvo com {total_publicacoes} publicações')
        else:
            print('❌ Problema com o texto extraído')
        
        # Limpar arquivo
        os.remove(caminho_pdf)
        
    else:
        print('❌ Falha ao baixar PDF')

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
