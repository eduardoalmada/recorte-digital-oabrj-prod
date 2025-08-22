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
from app.models import DiarioOficial, Advogado
from pdfminer.high_level import extract_text

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")


# ---------- BAIXAR PDF ----------
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

        time.sleep(5)  # espera página carregar

        iframes = driver.find_elements(By.TAG_NAME, 'iframe')

        for iframe in iframes:
            iframe_src = iframe.get_attribute('src') or ''

            if 'pdf.aspx' in iframe_src:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(3)

                    iframe_html = driver.page_source
                    iframe_filenames = re.findall(r'filename=([^&"\']+)', iframe_html)
                    print(f'📝 Filenames encontrados: {iframe_filenames}')

                    for filename in iframe_filenames:
                        if filename.startswith('/consultadje/temp/'):
                            filename = filename.replace('/consultadje/temp/', '')

                        pdf_url = f'https://www3.tjrj.jus.br/consultadje/temp/{filename}'
                        print(f'🎯 URL do PDF: {pdf_url}')

                        cookies = driver.get_cookies()
                        session = requests.Session()

                        for cookie in cookies:
                            session.cookies.set(cookie['name'], cookie['value'])

                        headers = {
                            'User-Agent': 'Mozilla/5.0',
                            'Accept': 'application/pdf, */*',
                            'Referer': driver.current_url
                        }

                        try:
                            response = session.get(pdf_url, headers=headers, timeout=15)
                            print(f'📊 Status: {response.status_code}, Tamanho: {len(response.content)}')

                            if response.status_code == 200 and response.content.startswith(b'%PDF'):
                                print('✅ PDF baixado com sucesso durante a sessão!')
                                driver.switch_to.default_content()
                                return response.content
                            else:
                                print('❌ Resposta não é um PDF válido')
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


# ---------- EXTRAÇÃO DE TEXTO ----------
def extrair_texto_pdf(caminho_pdf):
    try:
        return extract_text(caminho_pdf)
    except Exception as e:
        print(f'❌ Erro ao extrair texto: {e}')
        return ""


# ---------- WHATSAPP ----------
def enviar_mensagem_whatsapp(numero, mensagem):
    try:
        payload = {
            "session": "oab",
            "sessionkey": "oab",
            "number": numero,
            "text": mensagem
        }
        response = requests.post(WHATSAPP_API_URL, json=payload, timeout=15)
        if response.status_code == 200:
            print(f'✅ Mensagem enviada para {numero}')
        else:
            print(f'❌ Falha ao enviar mensagem ({response.status_code}): {response.text}')
    except Exception as e:
        print(f'❌ Erro no envio de mensagem: {e}')


# ---------- EXECUÇÃO ----------
def executar_scraper_djerj():
    hoje = datetime.now().date()
    print(f'📅 Verificando DJERJ de {hoje.strftime("%d/%m/%Y")}')

    caminho_pdf = f'temp/diario_{hoje.strftime("%Y%m%d")}.pdf'

    # já existe o PDF?
    if os.path.exists(caminho_pdf):
        print(f'📂 Usando PDF já existente: {caminho_pdf}')
    else:
        pdf_content = baixar_pdf_durante_sessao(hoje)
        if not pdf_content:
            print('❌ Falha ao obter PDF')
            return
        os.makedirs("temp", exist_ok=True)
        with open(caminho_pdf, 'wb') as f:
            f.write(pdf_content)
        print(f'✅ PDF salvo em {caminho_pdf}')

    # extrair texto
    texto = extrair_texto_pdf(caminho_pdf)

    if not texto or len(texto.strip()) < 100:
        print('❌ Texto do PDF inválido')
        return

    # buscar advogados cadastrados
    advogados = Advogado.query.all()
    for advogado in advogados:
        if advogado.nome_completo.upper() in texto.upper():
            print(f'✅ Advogado encontrado: {advogado.nome_completo}')

            # construir mensagem
            mensagem = (
                f"Olá, {advogado.nome_completo}. O Recorte Digital da OABRJ encontrou "
                f"publicações em seu nome no Diário da Justiça Eletrônico do Estado do Rio de Janeiro ({hoje.strftime('%d/%m/%Y')})."
            )

            # enviar whatsapp
            if advogado.whatsapp:
                enviar_mensagem_whatsapp(advogado.whatsapp, mensagem)
            else:
                print(f'⚠️ Advogado {advogado.nome_completo} não tem WhatsApp cadastrado')

    print("🏁 Processo finalizado.")


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
