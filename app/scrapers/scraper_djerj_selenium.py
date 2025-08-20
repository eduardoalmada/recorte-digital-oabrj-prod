import os
import re
import time
import logging
import requests
from io import BytesIO
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PyPDF2 import PdfReader
from requests.exceptions import RequestException

from app.models import db, Advogado, HtmlDjerjRaw, Publicacao

# --- CONFIGURAÇÃO ---
DJERJ_BASE_URL = "https://www3.tjrj.jus.br/consultadje/"
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL")  # UZAPI
WHATSAPP_SESSION = "oab"  # session key
MAX_RETRIES = 3
TIMEOUT_REQUESTS = 10

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- FUNÇÕES ---
def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=chrome_options)

def obter_url_pdf_dia():
    """Busca URL do PDF do dia atual."""
    data_hoje = datetime.today()
    driver = iniciar_driver()
    try:
        driver.get(DJERJ_BASE_URL)
        time.sleep(2)

        links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        for link in links:
            href = link.get_attribute("href")
            if data_hoje.strftime("%d%m%Y") in href:
                logging.info(f"URL do PDF do dia encontrada: {href}")
                return href
        logging.error("PDF do dia não encontrado.")
        return None
    finally:
        driver.quit()

def baixar_pdf(url: str) -> bytes:
    """Baixa PDF com retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=TIMEOUT_REQUESTS)
            response.raise_for_status()
            return response.content
        except RequestException as e:
            logging.warning(f"Tentativa {attempt} falhou para {url}: {e}")
            time.sleep(2)
    raise Exception(f"Não foi possível baixar PDF após {MAX_RETRIES} tentativas.")

def salvar_html_raw(conteudo_pdf: bytes):
    """Extrai texto do PDF e salva em html_djerj_raw."""
    pdf_reader = PdfReader(BytesIO(conteudo_pdf))
    texto = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    raw = HtmlDjerjRaw(data=datetime.today(), conteudo=texto)
    db.session.add(raw)
    db.session.commit()
    logging.info(f"PDF salvo no banco: id={raw.id}")
    return raw.id, texto

def buscar_publicacoes(raw_id: int, texto: str):
    """Procura nomes de advogados e cria publicações."""
    advogados = Advogado.query.all()
    texto_upper = texto.upper()
    for advogado in advogados:
        nome_regex = re.escape(advogado.nome_completo.upper())
        if re.search(nome_regex, texto_upper):
            pub = Publicacao(
                advogado_id=advogado.id,
                html_raw_id=raw_id,
                data=datetime.today(),
                conteudo=f"Nova publicação encontrada para {advogado.nome_completo}."
            )
            db.session.add(pub)
            db.session.commit()  # commit por publicação para garantir envio
            enviar_whatsapp(advogado, pub)

def enviar_whatsapp(advogado, publicacao):
    """Envia mensagem via UZAPI, com tratamento de erro e retries."""
    if not advogado.telefone:
        logging.warning(f"Advogado {advogado.nome_completo} sem telefone, não envia.")
        return

    payload = {
        "sessionkey": WHATSAPP_SESSION,
        "number": advogado.telefone,
        "text": f"Olá {advogado.nome_completo}, há uma nova publicação no Diário Oficial:\n{publicacao.conteudo}"
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(WHATSAPP_API_URL, json=payload, timeout=TIMEOUT_REQUESTS)
            response.raise_for_status()
            logging.info(f"WhatsApp enviado para {advogado.nome_completo}")
            return
        except RequestException as e:
            logging.warning(f"Tentativa {attempt} falhou WhatsApp para {advogado.nome_completo}: {e}")
            time.sleep(2)
    logging.error(f"Falha ao enviar WhatsApp para {advogado.nome_completo} após {MAX_RETRIES} tentativas.")

# --- MAIN ---
def main():
    logging.info("Iniciando scraper DJERJ do dia atual...")
    url_pdf = obter_url_pdf_dia()
    if not url_pdf:
        logging.error("Encerrando execução: PDF do dia não encontrado.")
        return

    pdf_bytes = baixar_pdf(url_pdf)
    raw_id, texto = salvar_html_raw(pdf_bytes)
    buscar_publicacoes(raw_id, texto)
    logging.info("Scraper concluído com sucesso.")

if __name__ == "__main__":
    main()
