# Scraper DJERJ – Render-ready: headless, sem caminho fixo de chromedriver,
# idempotente por dia, robusto com WebDriverWait e fallbacks.

import os
import re
import time
import logging
import requests
from datetime import date, datetime
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app import create_app, db
from app.models import Advogado, Publicacao, DiarioOficial

DJERJ_HOME = "https://www3.tjrj.jus.br/consultadje/"
TIMEOUT_PAGE = 20
TIMEOUT_REQ = 15

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _start_driver() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # user-agent “normal”
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    # Deixa o Selenium encontrar o chromedriver sozinho (Dockerfile já instala em /usr/local/bin)
    return webdriver.Chrome(options=chrome_options)


def _http_ok(url: str) -> bool:
    try:
        r = requests.head(url, timeout=TIMEOUT_REQ, allow_redirects=True)
        if r.status_code == 405:  # alguns servidores bloqueiam HEAD
            r = requests.get(url, timeout=TIMEOUT_REQ, stream=True)
        return 200 <= r.status_code < 400
    except Exception:
        return False


def _today_str_ptbr(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _find_pdf_in_home(driver: webdriver.Chrome, d: date) -> str | None:
    """Fallback rápido: procura âncoras .pdf na home contendo a data de hoje."""
    try:
        driver.get(DJERJ_HOME)
        WebDriverWait(driver, TIMEOUT_PAGE).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        anchors = driver.find_elements(By.TAG_NAME, "a")
        d_tokens = {d.strftime("%d/%m/%Y"), d.strftime("%d-%m-%Y"), d.strftime("%Y-%m-%d"), d.strftime("%d%m%Y")}
        for a in anchors:
            href = (a.get_attribute("href") or "").strip()
            text = (a.text or "").strip()
            if not href or ".pdf" not in href.lower():
                continue
            # heurística: a data de hoje aparece no texto ou no href
            if any(tok in text or tok in href for tok in d_tokens):
                pdf_url = href if href.startswith("http") else urljoin(DJERJ_HOME, href)
                if _http_ok(pdf_url):
                    logging.info(f"PDF (home) encontrado: {text} -> {pdf_url}")
                    return pdf_url
    except Exception as e:
        logging.warning(f"Fallback home falhou: {e}")
    return None


def _find_pdf_via_search(driver: webdriver.Chrome, d: date) -> str | None:
    """
    Fluxo 'oficial': abre a página, tenta ativar aba Pesquisa (se existir),
    preenche data inicial/final com hoje e clica Pesquisar; varre por links .pdf.
    """
    driver.get(DJERJ_HOME)
    WebDriverWait(driver, TIMEOUT_PAGE).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # 1) Tentar clicar em uma aba “Pesquisa” se existir
    try:
        candidates = driver.find_elements(By.XPATH, "//*[contains(translate(., 'PESQUISA', 'pesquisa'), 'pesquisa')]")
        if candidates:
            driver.execute_script("arguments[0].click();", candidates[0])
            time.sleep(1.5)
    except Exception:
        pass  # segue o baile

    # 2) Tentar localizar inputs de data por múltiplos seletores
    hoje_str = _today_str_ptbr(d)
    selectors = [
        (By.NAME, "dataInicial"),
        (By.CSS_SELECTOR, "input[name*='dataInicial' i]"),
        (By.CSS_SELECTOR, "input[placeholder*='Inicial' i]"),
        (By.XPATH, "//label[contains(., 'Data Inicial')]/following::input[1]"),
    ]

    data_inicial = None
    for by_, sel in selectors:
        try:
            data_inicial = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((by_, sel))
            )
            break
        except Exception:
            continue

    if not data_inicial:
        logging.info("Campo 'dataInicial' não visível. Tentando varredura direta por PDFs…")
        # Às vezes a busca é desnecessária; os links já estão na tela.
        return _first_pdf_on_page(driver, d)

    # Preenche datas
    try:
        data_inicial.clear()
        data_inicial.send_keys(hoje_str)
    except Exception:
        pass

    data_final = None
    for by_, sel in [
        (By.NAME, "dataFinal"),
        (By.CSS_SELECTOR, "input[name*='dataFinal' i]"),
        (By.CSS_SELECTOR, "input[placeholder*='Final' i]"),
        (By.XPATH, "//label[contains(., 'Data Final')]/following::input[1]"),
    ]:
        try:
            data_final = driver.find_element(by_, sel)
            break
        except Exception:
            continue

    if data_final:
        try:
            data_final.clear()
            data_final.send_keys(hoje_str)
        except Exception:
            pass

    # 3) Clica no botão "Pesquisar"
    try:
        btn = None
        for by_, sel in [
            (By.XPATH, "//button[contains(., 'Pesquisar')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//input[@type='submit' or @value='Pesquisar']"),
        ]:
            try:
                btn = driver.find_element(by_, sel)
                break
            except Exception:
                continue
        if btn:
            driver.execute_script("arguments[0].click();", btn)
            WebDriverWait(driver, TIMEOUT_PAGE).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
            )
            time.sleep(1.0)
    except Exception:
        pass

    # 4) Varre PDFs no resultado
    return _first_pdf_on_page(driver, d)


def _first_pdf_on_page(driver: webdriver.Chrome, d: date) -> str | None:
    anchors = driver.find_elements(By.TAG_NAME, "a")
    d_tokens = {d.strftime("%d/%m/%Y"), d.strftime("%d-%m-%Y"), d.strftime("%Y-%m-%d"), d.strftime("%d%m%Y")}
    for a in anchors:
        href = (a.get_attribute("href") or "").strip()
        text = (a.text or "").strip()
        if not href or ".pdf" not in href.lower():
            continue
        if any(tok in text or tok in href for tok in d_tokens) or "diário" in text.lower():
            pdf_url = href if href.startswith("http") else urljoin(DJERJ_HOME, href)
            if _http_ok(pdf_url):
                logging.info(f"PDF encontrado na página: {text} -> {pdf_url}")
                return pdf_url
    return None


def _grava_diario_e_cruza_advogados(pdf_url: str, d: date) -> int:
    """
    Salva o 'controle' do diário do dia e cria Publicações
    para cada advogado cujo nome esteja no PDF (via heurística de texto do link/URL).
    Obs.: aqui não baixamos o PDF (efêmero/Render). Se quiser OCR/texto, trate
    isso em um worker separado com storage persistente (S3).
    """
    # Idempotência do diário
    existente = DiarioOficial.query.filter_by(data_publicacao=d).first()
    if existente:
        return existente.id

    diario = DiarioOficial(
        fonte="DJERJ",
        data_publicacao=d,
        pdf_url=pdf_url,
    )
    db.session.add(diario)
    db.session.flush()  # pega id antes do commit

    # Heurística barata: se o nome do advogado aparece no URL do PDF ou no "slug",
    # cadastra uma Publicação. (Para precisão real, extraia texto do PDF em um job assíncrono.)
    slug = pdf_url.lower()

    advs = Advogado.query.all()
    pubs = 0
    for adv in advs:
        nome = (adv.nome_completo or "").strip()
        if not nome:
            continue
        # comparação tolerante (remove acentos simples)
        nome_norm = re.sub(r"[^a-z0-9]", "", nome.lower())
        slug_norm = re.sub(r"[^a-z0-9]", "", slug)
        if nome_norm and nome_norm in slug_norm:
            pub = Publicacao(
                advogado_id=adv.id,
                titulo=f"DJERJ {d.strftime('%d/%m/%Y')}",
                descricao=f"Publicação potencial para {adv.nome_completo}.",
                link=pdf_url,
                data=d,
                notificado=False,
            )
            db.session.add(pub)
            pubs += 1

    db.session.commit()
    logging.info(f"Diário {d} salvo. Publicações criadas: {pubs}")
    return diario.id


def executar_scraper():
    """
    Entrada única do scraper: roda só o DO de HOJE.
    - Evita duplicação pelo model DiarioOficial (unique por data).
    - Não baixa PDF (URL apenas).
    - Resiliente à variação de layout (fallbacks).
    """
    app = create_app()
    with app.app_context():
        hoje = date.today()
        # Já processado?
        if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
            logging.info(f"Diário de {hoje} já processado. Abortando.")
            return

        driver = _start_driver()
        try:
            pdf_url = _find_pdf_via_search(driver, hoje)
            if not pdf_url:
                logging.info("Busca via formulário falhou; tentando fallback na home…")
                pdf_url = _find_pdf_in_home(driver, hoje)

            if not pdf_url:
                logging.warning("Nenhum PDF de hoje encontrado.")
                return

            if not _http_ok(pdf_url):
                logging.warning(f"PDF encontrado, mas inacessível: {pdf_url}")
                return

            _grava_diario_e_cruza_advogados(pdf_url, hoje)

        finally:
            driver.quit()


if __name__ == "__main__":
    executar_scraper()
