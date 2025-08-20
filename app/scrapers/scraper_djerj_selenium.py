import os
import io
import time
import requests
import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PyPDF2 import PdfReader

from app import create_app
from app.models import db, Advogado, Publicacao, DiarioOficial


def configurar_driver():
    """Configura o Selenium para rodar em ambiente headless (Render)."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def baixar_pdf(url_pdf):
    """Faz download do PDF e retorna bytes."""
    resp = requests.get(url_pdf, timeout=60)
    resp.raise_for_status()
    return resp.content


def extrair_texto_pdf(pdf_bytes):
    """Extrai texto de um PDF (em bytes)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texto = []
    for page in reader.pages:
        try:
            texto.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texto)


def salvar_diario(data_publicacao, pdf_bytes):
    """Salva o PDF no banco se ainda não existir para a data."""
    diario = DiarioOficial.query.filter_by(data_publicacao=data_publicacao).first()
    if diario:
        return diario

    diario = DiarioOficial(
        data_publicacao=data_publicacao,
        fonte="DJERJ",
        arquivo_pdf=pdf_bytes,
    )
    db.session.add(diario)
    db.session.commit()
    return diario


def buscar_publicacoes(texto, data_publicacao):
    """Verifica se advogados aparecem no texto e salva publicações."""
    advogados = Advogado.query.all()
    encontrados = []

    for advogado in advogados:
        if advogado.nome.upper() in texto.upper():
            ja_tem = Publicacao.query.filter_by(
                advogado_id=advogado.id,
                data_publicacao=data_publicacao,
            ).first()

            if not ja_tem:
                pub = Publicacao(
                    advogado_id=advogado.id,
                    nome_advogado=advogado.nome,
                    conteudo=f"Encontrado no DJERJ {data_publicacao}",
                    data_publicacao=data_publicacao,
                )
                db.session.add(pub)
                encontrados.append(pub)

    if encontrados:
        db.session.commit()
    return encontrados


def executar_scraper():
    """Fluxo principal do scraper do DJERJ (apenas DO de hoje)."""
    hoje = datetime.date.today()

    # já tem DO de hoje salvo?
    if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
        print(f"[INFO] Diário de {hoje} já processado.")
        return

    driver = configurar_driver()
    try:
        url = "https://www3.tjrj.jus.br/consultadje/"
        driver.get(url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        link_pdf = None

        # procura link do PDF
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf") and str(hoje) in href:
                link_pdf = href
                break

        if not link_pdf:
            print(f"[WARN] Nenhum PDF encontrado para {hoje}")
            return

        if not link_pdf.startswith("http"):
            link_pdf = f"https://www3.tjrj.jus.br{link_pdf}"

        print(f"[INFO] Baixando PDF de {hoje}: {link_pdf}")
        pdf_bytes = baixar_pdf(link_pdf)

        # salva no banco
        salvar_diario(hoje, pdf_bytes)

        # extrai texto
        texto = extrair_texto_pdf(pdf_bytes)

        # busca publicações
        encontrados = buscar_publicacoes(texto, hoje)
        print(f"[INFO] Publicações encontradas: {len(encontrados)}")

    finally:
        driver.quit()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper()
