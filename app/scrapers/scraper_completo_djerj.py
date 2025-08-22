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

def encontrar_e_baixar_pdf(data):
    """Encontra a URL do PDF e baixa diretamente"""
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
        
        # Estratégia 1: Analisar o HTML da página para encontrar a URL do PDF
        page_source = driver.page_source
        print('📄 Analisando código fonte da página...')
        
        # Procurar URLs de PDF no código fonte
        pdf_urls = re.findall(r'https?://[^\s"]+\.pdf', page_source)
        print(f'📦 URLs PDF encontradas: {len(pdf_urls)}')
        for url in pdf_urls:
            print(f'  → {url}')
        
        # Procurar por parâmetros filename no código fonte
        filename_matches = re.findall(r'filename=([^&"\']+)', page_source)
        print(f'📝 Filenames encontrados: {filename_matches}')
        
        # Se encontrou filenames, tentar construir a URL
        if filename_matches:
            for filename in filename_matches:
                pdf_url = f'https://www3.tjrj.jus.br/consultadje/temp/{filename}'
                print(f'🎯 Tentando URL: {pdf_url}')
                
                # Tentar baixar diretamente
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/pdf, */*',
                    'Referer': 'https://www3.tjrj.jus.br/consultadje/'
                }
                
                try:
                    response = requests.get(pdf_url, headers=headers, timeout=15)
                    if response.status_code == 200 and response.content.startswith(b'%PDF'):
                        print('✅ PDF baixado com sucesso via URL direta!')
                        return response.content
                    else:
                        print(f'❌ Falha no download: Status {response.status_code}')
                except Exception as e:
                    print(f'❌ Erro ao baixar: {e}')
        
        # Estratégia 2: Analisar iframes
        print('🔍 Analisando iframes...')
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        
        for iframe in iframes:
            iframe_src = iframe.get_attribute('src') or ''
            print(f'Iframe: {iframe_src}')
            
            # Se for o iframe do PDF, analisar seu conteúdo
            if 'pdf.aspx' in iframe_src:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(2)
                    
                    # Analisar o HTML do iframe
                    iframe_html = driver.page_source
                    print('📊 Analisando conteúdo do iframe...')
                    
                    # Procurar URLs de PDF no iframe
                    iframe_pdf_urls = re.findall(r'https?://[^\s"]+\.pdf', iframe_html)
                    print(f'📦 URLs PDF no iframe: {len(iframe_pdf_urls)}')
                    for url in iframe_pdf_urls:
                        print(f'  → {url}')
                    
                    # Procurar por filenames no iframe
                    iframe_filenames = re.findall(r'filename=([^&"\']+)', iframe_html)
                    print(f'📝 Filenames no iframe: {iframe_filenames}')
                    
                    for filename in iframe_filenames:
                        pdf_url = f'https://www3.tjrj.jus.br/consultadje/temp/{filename}'
                        print(f'🎯 Tentando URL do iframe: {pdf_url}')
                        
                        # Tentar baixar
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': 'application/pdf, */*',
                            'Referer': 'https://www3.tjrj.jus.br/consultadje/'
                        }
                        
                        try:
                            response = requests.get(pdf_url, headers=headers, timeout=15)
                            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                                print('✅ PDF baixado do iframe!')
                                driver.switch_to.default_content()
                                return response.content
                        except Exception as e:
                            print(f'❌ Erro ao baixar do iframe: {e}')
                    
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
    
    # Encontrar e baixar PDF
    pdf_content = encontrar_e_baixar_pdf(hoje)
    
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
        print('❌ Falha ao encontrar e baixar PDF')

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
