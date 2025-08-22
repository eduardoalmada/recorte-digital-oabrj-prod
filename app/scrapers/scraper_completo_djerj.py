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
    """Clica no botão de download no visualizador de PDF para baixar o arquivo."""
    print(f'🔍 Iniciando download para {data.strftime("%d/%m/%Y")}...')
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Configurar download automático
    download_dir = '/tmp'
    chrome_options.add_experimental_option('prefs', {
        'download.default_directory': download_dir,
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True
    })
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        url = f'https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime("%d/%m/%Y")}&caderno=E&pagina=-1'
        driver.get(url)
        
        wait = WebDriverWait(driver, 20)
        
        # Esperar até que o iframe do PDF seja visível
        print('⏳ Esperando iframe do PDF...')
        pdf_iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[src*="pdf.aspx"]')))
        print('✅ Iframe do PDF encontrado.')

        # Mudar para o iframe do PDF
        driver.switch_to.frame(pdf_iframe)
        print('✅ Entrou no iframe do PDF')
        
        # 1. Esperar e clicar no botão de "Tools" (ferramentas) para abrir a toolbar secundária
        print('⏳ Esperando o botão de ferramentas...')
        toolbar_toggle_button = wait.until(EC.element_to_be_clickable((By.ID, 'secondaryToolbarToggle')))
        toolbar_toggle_button.click()
        print('✅ Toolbar secundária aberta com sucesso.')

        # 2. Esperar e clicar no botão de download que agora está visível
        print('⏳ Esperando o botão de download...')
        download_button = wait.until(EC.element_to_be_clickable((By.ID, 'secondaryDownload')))
        print('✅ Botão de download encontrado!')
        download_button.click()
        print('🖱️ Clique no botão de download realizado!')
        
        # Voltar para o contexto principal
        driver.switch_to.default_content()
        
        # Esperar que o download seja concluído (máximo de 60s)
        tempo_inicio = time.time()
        caminho_pdf_temporario = None
        while time.time() - tempo_inicio < 60:
            arquivos_baixados = glob.glob(os.path.join(download_dir, '*.pdf'))
            if arquivos_baixados:
                caminho_pdf_temporario = max(arquivos_baixados, key=os.path.getctime)
                if os.path.getsize(caminho_pdf_temporario) > 0:
                    print(f'✅ Download concluído: {os.path.basename(caminho_pdf_temporario)}')
                    with open(caminho_pdf_temporario, 'rb') as f:
                        pdf_content = f.read()
                    
                    if pdf_content.startswith(b'%PDF'):
                        os.remove(caminho_pdf_temporario)
                        return pdf_content
                    else:
                        print('❌ Arquivo baixado não é um PDF válido')
                        os.remove(caminho_pdf_temporario)
                        return None
            time.sleep(1)

        print('❌ Download do PDF falhou ou demorou demais.')
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
