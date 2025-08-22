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
import glob
from app import db
from app.models import DiarioOficial
from pdfminer.high_level import extract_text

def baixar_pdf_clicando_botao(data):
    """Clica no botão de download do visualizador de PDF"""
    print(f'🔍 Iniciando download para {data.strftime("%d/%m/%Y")}...')
    
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
        
        # Localizar o iframe do PDF
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        pdf_iframe = None
        
        for iframe in iframes:
            src = iframe.get_attribute('src') or ''
            if 'pdf.aspx' in src:
                pdf_iframe = iframe
                print(f'✅ Iframe do PDF encontrado: {src}')
                break
        
        if not pdf_iframe:
            print('❌ Iframe do PDF não encontrado')
            return None
        
        # Mudar para o iframe do PDF
        driver.switch_to.frame(pdf_iframe)
        print('✅ Entrou no iframe do PDF')
        time.sleep(3)
        
        # AGORA CLICAR NO BOTÃO DE DOWNLOAD QUE VOCÊ IDENTIFICOU!
        try:
            # Tentar encontrar o botão pelo ID
            download_button = driver.find_element(By.ID, 'download')
            print('✅ Botão de download encontrado pelo ID!')
        except:
            try:
                # Tentar encontrar pelo título
                download_button = driver.find_element(By.XPATH, '//button[@title="Save"]')
                print('✅ Botão de download encontrado pelo título!')
            except:
                try:
                    # Tentar encontrar pela classe
                    download_button = driver.find_element(By.CLASS_NAME, 'toolbarButton')
                    print('✅ Botão de download encontrado pela classe!')
                except:
                    print('❌ Botão de download não encontrado')
                    return None
        
        # Clicar no botão de download
        print('🖱️  Clicando no botão de download...')
        download_button.click()
        time.sleep(5)  # Esperar o download
        
        # Voltar para o contexto principal
        driver.switch_to.default_content()
        
        # Verificar se o arquivo foi baixado
        downloads = glob.glob('/tmp/*.pdf')
        if downloads:
            # Encontrar o arquivo mais recente
            latest_file = max(downloads, key=os.path.getctime)
            print(f'✅ Arquivo baixado: {latest_file}')
            
            # Ler o conteúdo do arquivo
            with open(latest_file, 'rb') as f:
                pdf_content = f.read()
            
            # Limpar arquivo temporário
            os.remove(latest_file)
            
            return pdf_content
        else:
            print('❌ Nenhum arquivo PDF foi baixado')
            return None
            
    except Exception as e:
        print(f'❌ Erro durante o download: {e}')
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
    
    # Baixar PDF clicando no botão
    pdf_content = baixar_pdf_clicando_botao(hoje)
    
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
        print('❌ Falha ao baixar PDF')

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
