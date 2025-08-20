import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import create_engine, text

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Database URL
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")

logging.info(f"📄 DATABASE_URL utilizada: {DATABASE_URL}")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
logging.info(f"📦 Banco configurado: {DATABASE_URL}")


def configurar_driver():
    """Configura o ChromeDriver para ambiente headless no Render"""
    options = Options()
    options.add_argument("--headless=new")  # modo headless moderno
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def buscar_publicacoes_djerj():
    """Acessa o DJERJ e retorna texto bruto das publicações"""
    url = "https://www3.tjrj.jus.br/consultadje/"
    logging.info(f"🌐 Acessando {url}")

    driver = configurar_driver()
    driver.get(url)

    try:
        # Espera até que a página carregue (máx 30s)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # pequeno delay extra p/ JS terminar
        texto = driver.page_source
    except Exception as e:
        logging.error(f"❌ Erro ao carregar página do DJERJ: {e}")
        texto = ""
    finally:
        driver.quit()

    return texto


def salvar_publicacao(texto):
    """Salva publicação bruta no banco (pode ser adaptado p/ parsing depois)"""
    if not texto:
        logging.warning("⚠ Nenhum texto recebido para salvar.")
        return

    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO publicacoes_djerj (conteudo) VALUES (:conteudo)"),
                {"conteudo": texto},
            )
        logging.info("✅ Publicação salva no banco com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro ao salvar no banco: {e}")


def processar_publicacoes_djerj():
    """Pipeline principal: busca -> salva"""
    logging.info("🚀 Iniciando busca de publicações no DJERJ...")
    texto_publicacoes = buscar_publicacoes_djerj()
    salvar_publicacao(texto_publicacoes)
    logging.info("🏁 Processo concluído.")


if __name__ == "__main__":
    processar_publicacoes_djerj()
