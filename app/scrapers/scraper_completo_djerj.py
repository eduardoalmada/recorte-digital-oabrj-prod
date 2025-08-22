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
        
        # Estratégia 1: Tentar executar JavaScript para mostrar botões ocultos
        print('🔄 Tentando mostrar botões ocultos...')
        driver.execute_script("""
            // Tentar mostrar botões ocultos
            var hiddenButtons = document.querySelectorAll('.hiddenMediumView, .hiddenLargeView, [style*="display: none"]');
            hiddenButtons.forEach(function(btn) {
                btn.style.display = 'block';
                btn.style.visibility = 'visible';
            });
            
            // Tentar mostrar a toolbar secundária
            var secondaryToolbar = document.getElementById('secondaryToolbar');
            if (secondaryToolbar) {
                secondaryToolbar.classList.remove('hidden');
            }
        """)
        
        time.sleep(2)
        
        # Estratégia 2: Procurar o botão de múltiplas formas
        print('🔍 Procurando botão de download...')
        
        # Lista de seletores para tentar
        selectors = [
            '#download',  # Por ID
            'button[title="Save"]',  # Por título
            'button[data-l10n-id="save"]',  # Por data attribute
            '.toolbarButton',  # Por classe
            'button[onclick*="download"]',  # Por onclick
        ]
        
        download_button = None
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    download_button = elements[0]
                    print(f'✅ Botão encontrado por seletor: {selector}')
                    break
            except:
                continue
        
        # Estratégia 3: Buscar por texto usando JavaScript
        if not download_button:
            print('🔍 Procurando botão por texto...')
            try:
                elements = driver.execute_script("""
                    return Array.from(document.querySelectorAll('button')).filter(btn => 
                        btn.textContent.includes('Save') || 
                        btn.textContent.includes('Download') || 
                        btn.textContent.includes('Salvar')
                    );
                """)
                if elements and len(elements) > 0:
                    download_button = elements[0]
                    print(f'✅ Botão encontrado por texto: {download_button.text}')
            except:
                pass
        
        if not download_button:
            print('❌ Botão de download não encontrado após todas as tentativas')
            print('📋 Debug: Listando todos os botões disponíveis...')
            
            # Listar todos os botões para debug
            all_buttons = driver.find_elements(By.TAG_NAME, 'button')
            print(f'Total de botões: {len(all_buttons)}')
            for i, btn in enumerate(all_buttons):
                print(f'Botão {i+1}: Texto="{btn.text}", ID="{btn.get_attribute("id")}", Classe="{btn.get_attribute("class")}"')
            
            return None
        
        # Estratégia 4: Clicar via JavaScript se necessário
        print('🖱️  Tentando clicar no botão...')
        try:
            # Primeiro tentar clicar normalmente
            download_button.click()
            print('✅ Clique normal realizado')
        except:
            try:
                # Se falhar, tentar via JavaScript
                driver.execute_script("arguments[0].click();", download_button)
                print('✅ Clique via JavaScript realizado')
            except Exception as e:
                print(f'❌ Erro ao clicar: {e}')
                return None
        
        print('⏳ Aguardando download...')
        time.sleep(8)  # Esperar mais tempo para download
        
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
                os.remove(latest_file)
                return None
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
