# app/scrapers/scraper_djerj_dinamico.py
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import re
from app import db
from app.models import DiarioOficial
from pdfminer.high_level import extract_text

def encontrar_url_pdf_diaria(data):
    """Encontra a URL do PDF do dia usando Selenium"""
    print(f'🔍 Buscando PDF para {data.strftime("%d/%m/%Y")}...')
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Acessar a página principal com a data específica
        url = f'https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime("%d/%m/%Y")}&caderno=E&pagina=-1'
        driver.get(url)
        
        # Esperar o carregamento (usando wait explícito)
        wait = WebDriverWait(driver, 15)
        
        # Esperar até que os iframes estejam carregados
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
        time.sleep(3)  # Espera adicional para garantir carregamento completo
        
        # Procurar o iframe do PDF
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        pdf_iframe = None
        
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'pdf.aspx' in src:
                pdf_iframe = iframe
                break
        
        if not pdf_iframe:
            print('❌ Iframe do PDF não encontrado')
            return None
        
        # Mudar para o iframe do PDF
        driver.switch_to.frame(pdf_iframe)
        time.sleep(2)
        
        # Procurar a URL do PDF dentro do iframe
        pdf_elements = driver.find_elements(By.XPATH, '//*[@src] | //*[@href] | //*[contains(@src, ".pdf")] | //*[contains(@href, ".pdf")]')
        
        pdf_url = None
        for element in pdf_elements:
            src = element.get_attribute('src') or ''
            href = element.get_attribute('href') or ''
            
            # Verificar se é um link de PDF
            for link in [src, href]:
                if link and '.pdf' in link.lower() and 'filename=' in link:
                    # Extrair a parte do filename
                    pdf_filename = link.split('filename=')[1]
                    pdf_direct_url = f'https://www3.tjrj.jus.br/consultadje/temp/{pdf_filename}'
                    pdf_url = pdf_direct_url
                    break
            
            if pdf_url:
                break
        
        driver.switch_to.default_content()
        
        if pdf_url:
            print(f'✅ URL do PDF encontrada: {pdf_url}')
            return pdf_url
        else:
            print('❌ URL do PDF não encontrada no iframe')
            return None
            
    except Exception as e:
        print(f'❌ Erro ao buscar URL do PDF: {e}')
        return None
    finally:
        driver.quit()

def baixar_pdf(url):
    """Baixa o PDF da URL fornecida"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf, */*',
        'Referer': 'https://www3.tjrj.jus.br/consultadje/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200 and 'pdf' in response.headers.get('content-type', '').lower():
            return response.content
        else:
            print(f'❌ Falha no download: Status {response.status_code}, Content-Type: {response.headers.get("content-type")}')
            return None
            
    except Exception as e:
        print(f'❌ Erro ao baixar PDF: {e}')
        return None

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
    
    # Encontrar URL do PDF do dia
    pdf_url = encontrar_url_pdf_diaria(hoje)
    
    if not pdf_url:
        print('❌ Não foi possível encontrar o PDF do dia')
        return
    
    # Baixar PDF
    pdf_content = baixar_pdf(pdf_url)
    
    if pdf_content:
        # Salvar temporariamente
        os.makedirs('temp', exist_ok=True)
        caminho_pdf = f'temp/diario_{hoje.strftime("%Y%m%d")}.pdf'
        
        with open(caminho_pdf, 'wb') as f:
            f.write(pdf_content)
        
        print(f'✅ PDF baixado: {len(pdf_content)} bytes')
        
        # Extrair texto
        texto = extrair_texto_pdf(caminho_pdf)
        
        if texto:
            # Verificar se contém conteúdo relevante
            if len(texto.strip()) > 100:
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
                print('❌ PDF vazio ou com pouco texto')
        else:
            print('❌ Não foi possível extrair texto do PDF')
        
        # Limpar arquivo
        os.remove(caminho_pdf)
        
    else:
        print('❌ Falha ao baixar PDF')

if __name__ == '__main__':
    executar_scraper_djerj()
