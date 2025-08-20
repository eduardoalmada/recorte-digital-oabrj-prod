# app/scrapers/scraper_djerj_selenium.py - VERSÃO CORRETA
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
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def pesquisar_diario_do_dia(driver):
    """Faz pesquisa no sistema consultadje para encontrar o diário de hoje"""
    try:
        print("🔍 Acessando sistema de pesquisa...")
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(5)
        
        # Verifica se carregou a página correta
        if "Pesquisa DJERJ" not in driver.title:
            print(f"❌ Página errada: {driver.title}")
            return None
        
        print("✅ Página de pesquisa carregada")
        
        # 1. CLICA NA ABA "PESQUISA"
        try:
            aba_pesquisa = driver.find_element(By.XPATH, "//a[@href='#pills-pesquisa']")
            aba_pesquisa.click()
            print("✅ Clicou na aba 'Pesquisa'")
            time.sleep(2)
        except:
            print("⚠️ Não encontrou aba pesquisa, continuando...")
        
        # 2. PREENCHE DATA DE HOJE
        hoje = date.today()
        data_formatada = hoje.strftime("%d/%m/%Y")
        
        # Limpa e preenche data inicial
        try:
            data_inicial = driver.find_element(By.NAME, "dataInicial")
            data_inicial.clear()
            data_inicial.send_keys(data_formatada)
            print(f"✅ Preencheu data inicial: {data_formatada}")
        except:
            print("❌ Não encontrou campo data inicial")
            return None
        
        # Preenche data final (mesma data)
        try:
            data_final = driver.find_element(By.NAME, "dataFinal")
            data_final.clear()
            data_final.send_keys(data_formatada)
            print(f"✅ Preencheu data final: {data_formatada}")
        except:
            print("⚠️ Não encontrou campo data final")
        
        # 3. CLICA EM PESQUISAR
        try:
            btn_pesquisar = driver.find_element(By.XPATH, "//button[contains(text(), 'Pesquisar')]")
            btn_pesquisar.click()
            print("✅ Clicou em Pesquisar")
            time.sleep(5)  # Espera resultados
        except:
            print("❌ Não encontrou botão Pesquisar")
            return None
        
        # 4. VERIFICA RESULTADOS
        print("🔍 Procurando resultados...")
        
        # Tenta encontrar links de PDF nos resultados
        links = driver.find_elements(By.TAG_NAME, "a")
        pdf_url = None
        
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            
            # Procura links de PDF que contenham a data
            if (".pdf" in href.lower() and 
                (data_formatada in text or data_formatada in href or "Diário" in text)):
                pdf_url = href
                print(f"✅ PDF encontrado: {text} -> {href}")
                break
        
        if not pdf_url:
            print("❌ Nenhum PDF encontrado nos resultados")
            # Tira screenshot para debug
            driver.save_screenshot("/tmp/consultadje_resultados.png")
            print("📸 Screenshot dos resultados: /tmp/consultadje_resultados.png")
            return None
        
        return pdf_url
        
    except Exception as e:
        print(f"❌ Erro na pesquisa: {e}")
        import traceback
        traceback.print_exc()
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
            pdf_url = pesquisar_diario_do_dia(driver)
            
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
