# app/scrapers/debug_consultadje.py - VERSÃO CORRIGIDA
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Configurações para evitar o erro
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    
    # Configura diretório temporário único
    chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_{int(time.time())}")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def debug_consultadje():
    print("🚀 Iniciando debug do consultadje...")
    
    driver = iniciar_driver()
    
    try:
        print("🌐 Acessando https://www3.tjrj.jus.br/consultadje/")
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(8)  # Mais tempo para carregar
        
        print(f"📄 Título: {driver.title}")
        print(f"🌐 URL: {driver.current_url}")
        
        # Salva HTML completo
        with open("/tmp/consultadje_html.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("📝 HTML salvo: /tmp/consultadje_html.html")
        
        # Salva screenshot
        driver.save_screenshot("/tmp/consultadje_screenshot.png")
        print("📸 Screenshot: /tmp/consultadje_screenshot.png")
        
        # Analisa estrutura
        print("\n🔍 Analisando estrutura...")
        
        # Links
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"🔗 Total de links: {len(links)}")
        
        print("\n📋 Primeiros 10 links:")
        for i, link in enumerate(links[:10]):
            href = link.get_attribute("href") or ""
            text = link.text.strip()[:50]  # Limita texto
            print(f"  {i+1}. {text} -> {href}")
        
        # Links PDF
        pdf_links = []
        for link in links:
            href = link.get_attribute("href") or ""
            if ".pdf" in href.lower():
                text = link.text.strip()
                pdf_links.append((text, href))
        
        print(f"\n📊 PDFs encontrados: {len(pdf_links)}")
        for i, (text, href) in enumerate(pdf_links[:5]):
            print(f"  📄 {i+1}. {text} -> {href}")
        
        # Tenta encontrar a data de hoje
        from datetime import date
        hoje = date.today().strftime("%d/%m/%Y")
        print(f"\n📅 Procurando data: {hoje}")
        
        # Procura por elementos com a data
        elementos = driver.find_elements(By.XPATH, f"//*[contains(text(), '{hoje}')]")
        print(f"📆 Elementos com data de hoje: {len(elementos)}")
        
        for i, elem in enumerate(elementos[:3]):
            print(f"  {i+1}. {elem.text[:100]}...")
            
        # Procura elementos comuns
        print("\n🔎 Elementos com 'Diário' ou 'DJE':")
        elementos_diario = driver.find_elements(By.XPATH, "//*[contains(text(), 'Diário') or contains(text(), 'DJE')]")
        for i, elem in enumerate(elementos_diario[:5]):
            print(f"  {i+1}. {elem.text[:80]}...")
            
    except Exception as e:
        print(f"❌ Erro durante debug: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            driver.quit()
            print("✅ Driver finalizado")
        except:
            pass

if __name__ == "__main__":
    debug_consultadje()
