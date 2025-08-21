import os
import re
import time
import logging
import requests
from datetime import date
from sqlalchemy import text

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pdfminer.high_level import extract_text
from io import BytesIO

from app import create_app, db
from app.models import Advogado, Publicacao, DiarioOficial

DJERJ_BASE = "https://www3.tjrj.jus.br/consultadje/"
TIMEOUT = 30
MAX_RETRIES = 3
CHUNK_SIZE = 1000  # quantidade de advogados por vez

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _start_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)


def _format_date_ptbr(d):
    return d.strftime("%d/%m/%Y")


def _get_pdf_url(driver, data):
    """Acessa a página principal e retorna a URL do PDF do dia"""
    url = f"{DJERJ_BASE}consultaDJE.aspx?dtPub={_format_date_ptbr(data)}&caderno=E&pagina=-1"
    driver.get(url)

    try:
        iframe = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        src = iframe.get_attribute("src")
        match = re.search(r"filename=(.*\.pdf)", src)
        if match:
            filename = match.group(1)
            return f"{DJERJ_BASE}temp/{filename}"
    except Exception as e:
        logging.error(f"Erro ao extrair PDF: {e}")
    return None


def _baixar_pdf(pdf_url):
    """Baixa o PDF e retorna o conteúdo em bytes"""
    resp = requests.get(pdf_url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _extrair_texto_pdf(pdf_bytes):
    """Extrai texto do PDF usando pdfminer"""
    return extract_text(BytesIO(pdf_bytes))


def _salvar_diario(data, pdf_url):
    diario = DiarioOficial(fonte="DJERJ", data_publicacao=data, arquivo_pdf=pdf_url)
    db.session.add(diario)
    db.session.commit()
    return diario.id


def _salvar_publicacoes(data, pdf_url, advogados_encontrados):
    """Salva publicações no banco"""
    diario_id = _salvar_diario(data, pdf_url)
    total = 0

    for adv in advogados_encontrados:
        pub = Publicacao(
            advogado_id=adv.id,
            titulo=f"DJERJ {data.strftime('%d/%m/%Y')}",
            descricao=f"Publicação encontrada para {adv.nome_completo}",
            link=pdf_url,
            data=data,
            notificado=False
        )
        db.session.add(pub)
        total += 1

    db.session.commit()
    return total


def executar_scraper_otimizado():
    """Fluxo principal"""
    app = create_app()
    with app.app_context():
        hoje = date.today()

        # já processado hoje?
        if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
            logging.info(f"Diário de {hoje} já processado.")
            return

        driver = _start_driver()
        try:
            pdf_url = _get_pdf_url(driver, hoje)
            if not pdf_url:
                logging.warning("Nenhum PDF encontrado hoje.")
                return

            logging.info(f"📄 PDF encontrado: {pdf_url}")
            pdf_bytes = _baixar_pdf(pdf_url)
            texto = _extrair_texto_pdf(pdf_bytes)

            # busca em chunks
            total_publicacoes = 0
            offset = 0
            while True:
                advogados = Advogado.query.offset(offset).limit(CHUNK_SIZE).all()
                if not advogados:
                    break

                encontrados = []
                for adv in advogados:
                    if adv.nome_completo and adv.nome_completo.upper() in texto.upper():
                        encontrados.append(adv)
                        continue
                    if adv.numero_oab and adv.numero_oab in texto:
                        encontrados.append(adv)
                        continue

                if encontrados:
                    total_publicacoes += _salvar_publicacoes(hoje, pdf_url, encontrados)
                    for adv in encontrados:
                        logging.info(f"✅ Encontrado: {adv.nome_completo}")

                offset += CHUNK_SIZE

            logging.info(f"🔍 Total publicações salvas: {total_publicacoes}")

        except Exception as e:
            logging.error(f"❌ Erro geral: {e}")
        finally:
            driver.quit()


if __name__ == "__main__":
    executar_scraper_otimizado()
