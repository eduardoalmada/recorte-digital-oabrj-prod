# app/scrapers/scraper_completo_djerj.py
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
import glob
from app import db
from app.models import DiarioOficial
from pdfminer.high_level import extract_text

def baixar_pdf_diretamente_selenium(data):
    """Usa Selenium para encontrar e baixar o PDF diretamente"""
    print(f'🔍 Buscando e baixando PDF para {data.strftime("%d/%m/%Y")}...')
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Configurar download automático
    chrome_options.add_experimental_option('prefs', {
        'download.default_directory': '/tmp',
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True
    })
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = f'https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime("%d/%m/%Y")}&caderno=E&pagina=-1'
        driver.get(url)
        
        # Esperar carregamento
        time.sleep(5)
        
        # Procurar o link de download direto dentro da página
        links = driver.find_elements(By.XPATH, '//a[contains(@href, ".pdf")] | //button[contains(@onclick, ".pdf")]')
        print(f'Links PDF encontrados: {len(links)}')
        
        for link in links:
            href = link.get_attribute('href') or ''
            onclick = link.get_attribute('onclick') or ''
            print(f'Link: {href}, OnClick: {onclick[:100]}...')
        
        # Alternativa: tentar encontrar o iframe e interagir com ele
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'pdf' in src.lower():
                print(f'Iframe PDF: {src}')
                
                # Mudar para o iframe
                driver.switch_to.frame(iframe)
                time.sleep(2)
                
                # Procurar botão de download dentro do iframe
                download_buttons = driver.find_elements(By.XPATH, '//*[contains(text(), "Download")] | //*[contains(@title, "Download")] | //*[contains(@class, "download")]')
                print(f'Botões download no iframe: {len(download_buttons)}')
                
                for btn in download_buttons:
                    print(f'Botão: {btn.text}, Title: {btn.get_attribute("title")}')
                    try:
                        btn.click()
                        print('✅ Clicou no botão de download!')
                        time.sleep(5)
                        break
                    except:
                        continue
                
                driver.switch_to.default_content()
        
        # Verificar se algum arquivo foi baixado
        downloads = glob.glob('/tmp/*.pdf')
        if downloads:
            print(f'📁 Arquivos baixados: {downloads}')
            # Ler o arquivo baixado mais recente
            latest_file = max(downloads, key=os.path.getctime)
            with open(latest_file, 'rb') as f:
                pdf_content = f.read()
            
            # Limpar arquivo temporário
            os.remove(latest_file)
            return pdf_content
        else:
            print('❌ Nenhum arquivo PDF foi baixado')
            return None
            
    except Exception as e:
        print(f'❌ Erro no Selenium: {e}')
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
    
    # Baixar PDF diretamente usando Selenium
    pdf_content = baixar_pdf_diretamente_selenium(hoje)
    
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
    from app import create_app
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
