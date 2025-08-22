# app/scrapers/scraper_completo_djerj.py

import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import re
from pdfminer.high_level import extract_text

from app import db, create_app
from app.models import DiarioOficial, Advogado, AdvogadoPublicacao


# ========== DOWNLOAD PDF ==========

def baixar_pdf_durante_sessao(data):
    """Baixa o PDF durante a sessão do Selenium para evitar expiração"""
    print(f'🔍 Buscando PDF para {data.strftime("%d/%m/%Y")}...')

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        url = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime('%d/%m/%Y')}&caderno=E&pagina=-1"
        driver.get(url)

        time.sleep(5)

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for iframe in iframes:
            iframe_src = iframe.get_attribute("src") or ""

            if "pdf.aspx" in iframe_src:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(3)

                    iframe_html = driver.page_source
                    iframe_filenames = re.findall(r"filename=([^&\"']+)", iframe_html)
                    print(f"📝 Filenames encontrados: {iframe_filenames}")

                    for filename in iframe_filenames:
                        if filename.startswith("/consultadje/temp/"):
                            filename = filename.replace("/consultadje/temp/", "")

                        pdf_url = f"https://www3.tjrj.jus.br/consultadje/temp/{filename}"
                        print(f"🎯 URL do PDF: {pdf_url}")

                        cookies = driver.get_cookies()
                        session = requests.Session()

                        for cookie in cookies:
                            session.cookies.set(cookie["name"], cookie["value"])

                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "application/pdf, */*",
                            "Referer": driver.current_url,
                        }

                        response = session.get(pdf_url, headers=headers, timeout=15)
                        print(f"📊 Status: {response.status_code}, Tamanho: {len(response.content)}")

                        if response.status_code == 200 and response.content.startswith(b"%PDF"):
                            print("✅ PDF baixado com sucesso durante a sessão!")
                            driver.switch_to.default_content()
                            return response.content

                except Exception as e:
                    print(f"❌ Erro ao analisar iframe: {e}")
                    driver.switch_to.default_content()

        return None

    finally:
        driver.quit()


# ========== EXTRAÇÃO PDF ==========

def extrair_texto_pdf(caminho_pdf):
    try:
        return extract_text(caminho_pdf)
    except Exception as e:
        print(f"❌ Erro ao extrair texto: {e}")
        return ""


# ========== WHATSAPP ==========

def enviar_whatsapp(telefone, mensagem):
    """Envia mensagem pelo WhatsApp API da OABRJ"""
    try:
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        payload = {
            "session": "oab",
            "number": telefone,
            "text": mensagem,
        }
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"✅ Mensagem enviada para {telefone}")
        else:
            print(f"❌ Falha ao enviar mensagem ({telefone}): {r.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp: {e}")


# ========== SCRAPER PRINCIPAL ==========

def executar_scraper_djerj():
    hoje = datetime.now().date()
    print(f"📅 Verificando DJERJ de {hoje.strftime('%d/%m/%Y')}")

    # já processado?
    if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
        print("⚠️ DJERJ já processado hoje.")
        return

    # baixar pdf
    pdf_content = baixar_pdf_durante_sessao(hoje)
    if not pdf_content:
        print("❌ Não foi possível baixar PDF")
        return

    os.makedirs("temp", exist_ok=True)
    caminho_pdf = f"temp/diario_{hoje.strftime('%Y%m%d')}.pdf"
    with open(caminho_pdf, "wb") as f:
        f.write(pdf_content)

    texto = extrair_texto_pdf(caminho_pdf)

    # criar diário no banco
    diario = DiarioOficial(
        data_publicacao=hoje,
        edicao="E",
        total_publicacoes=0,
        arquivo_pdf=caminho_pdf,
    )
    db.session.add(diario)
    db.session.commit()

    total_diario = 0

    # buscar advogados
    advogados = Advogado.query.all()
    for adv in advogados:
        qtd_mencoes = texto.upper().count(adv.nome_completo.upper())
        if qtd_mencoes > 0:
            total_diario += qtd_mencoes

            pub = AdvogadoPublicacao(
                advogado_id=adv.id,
                diario_id=diario.id,
                data_publicacao=hoje,
                qtd_mencoes=qtd_mencoes,
            )
            db.session.add(pub)

            titulo = (
                f"Olá, {adv.nome_completo}. "
                f"O Recorte Digital da OABRJ encontrou {qtd_mencoes} "
                f"publicações em seu nome no Diário da Justiça Eletrônico do Estado do Rio de Janeiro ({hoje.strftime('%d/%m/%Y')})."
            )
            enviar_whatsapp(adv.whatsapp, titulo)

    diario.total_publicacoes = total_diario
    db.session.commit()

    print(f"✅ Diário {hoje} salvo com {total_diario} menções no total")

    os.remove(caminho_pdf)


# ========== MAIN ==========

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
