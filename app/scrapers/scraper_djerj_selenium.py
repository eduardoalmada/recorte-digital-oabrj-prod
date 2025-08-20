# app/scrapers/scraper_djerj_selenium.py - VERSÃO CORRIGIDA PARA consultadje
import os
import time
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import requests

from app import create_app, db
from app.models import DiarioOficial

def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def encontrar_diario_do_dia(driver):
    """Encontra o link para o diário do dia atual no consultadje"""
    try:
        print("🔍 Acessando consultadje...")
        
        # Acessa a página correta
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(5)
        
        # Tira screenshot para debug
        driver.save_screenshot("/tmp/consultadje_debug.png")
        print("📸 Screenshot salva: /tmp/consultadje_debug.png")
        
        # Verifica se está na página correta
        if "Consultadje" not in driver.title:
            print(f"❌ Página não é o Consultadje: {driver.title}")
            return None
        
        hoje = date.today()
        data_formatada = hoje.strftime("%d/%m/%Y")
        print(f"📅 Procurando diário de {data_formatada}")
        
        # Método 1: Procura por data nos links (mais comum)
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            pdf_url = None
            
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                
                # Procura por links de PDF com a data de hoje
                if (".pdf" in href.lower() and 
                    (data_formatada in text or data_formatada in href)):
                    pdf_url = href
                    print(f"✅ Encontrado PDF: {text} -> {href}")
                    break
            
            if pdf_url:
                return pdf_url
        except Exception as e:
            print(f"⚠️ Erro ao procurar links: {e}")
        
        # Método 2: Procura em tabelas ou divs específicas
        try:
            # Tenta encontrar elementos comuns no consultadje
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Diário') or contains(text(), 'DJE')]")
            for element in elements:
                text = element.text
                if data_formatada in text:
                    print(f"📄 Elemento encontrado: {text}")
                    # Tenta encontrar link próximo
                    parent = element.find_element(By.XPATH, "./..")
                    links = parent.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and ".pdf" in href.lower():
                            print(f"✅ PDF encontrado: {href}")
                            return href
        except Exception as e:
            print(f"⚠️ Erro método 2: {e}")
        
        print("❌ Diário do dia não encontrado")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao procurar diário: {e}")
        return None

def executar_scraper():
    app = create_app()

    with app.app_context():
        hoje = datetime.now().date()
        print(f"📅 Rodando scraper para o dia {hoje}")

        # Verifica se já existe
        if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
            print(f"📌 Diário Oficial de {hoje} já armazenado.")
            return

        driver = iniciar_driver()
        try:
            pdf_url = encontrar_diario_do_dia(driver)
            
            if not pdf_url:
                print("⚠️ Nenhum diário encontrado para hoje.")
                return

            # Verifica se o PDF é acessível
            try:
                response = requests.head(pdf_url, timeout=10)
                if response.status_code != 200:
                    print(f"❌ PDF não acessível: Status {response.status_code}")
                    return
            except Exception as e:
                print(f"❌ Erro ao verificar PDF: {e}")
                return

            # Salva no banco
            diario = DiarioOficial(
                data_publicacao=hoje,
                fonte="DJERJ",
                arquivo_pdf=pdf_url
            )
            db.session.add(diario)
            db.session.commit()
            
            print(f"✅ Diário salvo: {pdf_url}")

        except Exception as e:
            print(f"❌ Erro no scraper: {e}")
            db.session.rollback()
        finally:
            driver.quit()

if __name__ == "__main__":
    executar_scraper()
