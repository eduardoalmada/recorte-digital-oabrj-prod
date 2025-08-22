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
        
        # Esperar carregamento com wait explícito
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
        time.sleep(3)
        
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
        
        # Esperar mais tempo para o PDF.js carregar completamente
        time.sleep(5)
        
        # ESTRATÉGIA DIRETA: CLICAR NO BOTÃO secondaryDownload QUE VOCÊ IDENTIFICOU!
        print('🔍 Procurando botão secondaryDownload...')
        
        try:
            # Tentar encontrar o botão pelo ID exato
            download_button = driver.find_element(By.ID, 'secondaryDownload')
            print('✅ Botão secondaryDownload encontrado!')
            
        except:
            print('❌ Botão secondaryDownload não encontrado pelo ID')
            
            # Tentar alternativas
            try:
                download_button = driver.find_element(By.CSS_SELECTOR, 'button[title="Save"]')
                print('✅ Botão encontrado pelo título "Save"')
            except:
                try:
                    download_button = driver.find_element(By.CSS_SELECTOR, '.secondaryToolbarButton')
                    print('✅ Botão encontrado pela classe secondaryToolbarButton')
                except:
                    print('❌ Nenhum botão de download encontrado')
                    return None
        
        # Primeiro: abrir a toolbar secundária se necessário
        print('🚀 Abrindo toolbar secundária...')
        try:
            # Procurar botão para abrir toolbar secundária
            toolbar_toggle = driver.find_element(By.ID, 'secondaryToolbarToggle')
            driver.execute_script("arguments[0].click();", toolbar_toggle)
            print('✅ Toolbar secundária aberta')
            time.sleep(2)
        except:
            print('⚠️  Não foi possível abrir toolbar secundária, tentando diretamente...')
        
        # Clicar no botão de download
        print('🖱️  Clicando no botão de download...')
        try:
            # Usar JavaScript para garantir o clique
            driver.execute_script("arguments[0].click();", download_button)
            print('✅ Clique no botão de download realizado!')
        except Exception as e:
            print(f'❌ Erro ao clicar: {e}')
            
            # Tentar método alternativo: simular evento de clique
            try:
                driver.execute_script("""
                    var event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    arguments[0].dispatchEvent(event);
                """, download_button)
                print('✅ Clique alternativo realizado!')
            except:
                print('❌ Falha em todos os métodos de clique')
                return None
        
        print('⏳ Aguardando download...')
        time.sleep(10)  # Esperar o download
        
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
            
            # Verificar se é um PDF válido
            if pdf_content.startswith(b'%PDF'):
                print('✅ PDF válido baixado!')
                # Limpar arquivo temporário
                os.remove(latest_file)
                return pdf_content
            else:
                print('❌ Arquivo baixado não é um PDF válido')
                print('Primeiros bytes:', pdf_content[:20])
                os.remove(latest_file)
                return None
        else:
            print('❌ Nenhum arquivo PDF foi baixado')
            # Listar arquivos em /tmp para debug
            all_files = glob.glob('/tmp/*')
            print(f'Arquivos em /tmp: {all_files}')
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
