# app/scrapers/scraper_djerj_selenium.py - VERSÃO CORRIGIDA
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
    """Encontra o link para o diário do dia atual"""
    try:
        print("🔍 Procurando diário do dia...")
        
        # Acessa a página correta do DJERJ
        driver.get("https://dje.tjrn.jus.br/dje/")
        time.sleep(3)
        
        # Tenta encontrar o diário de hoje por diferentes métodos
        hoje = date.today()
        data_formatada = hoje.strftime("%d/%m/%Y")
        
        print(f"📅 Procurando diário de {data_formatada}")
        
        # Método 1: Procura por link com a data
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                
                if data_formatada in text or data_formatada in href:
                    print(f"✅ Encontrado diário: {text}")
                    return href
        except:
            pass
        
        # Método 2: Procura na seção de diários recentes
        try:
            sections = driver.find_elements(By.TAG_NAME, "section")
            for section in sections:
                if "Diário de Justiça" in section.text:
                    links = section.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        if data_formatada in link.text:
                            pdf_url = link.get_attribute("href")
                            print(f"✅ Encontrado PDF: {pdf_url}")
                            return pdf_url
        except:
            pass
        
        print("❌ Diário do dia não encontrado na página principal")
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
            except:
                print("❌ Erro ao verificar PDF")
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
