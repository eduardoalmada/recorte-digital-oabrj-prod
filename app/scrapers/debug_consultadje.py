# app/scrapers/debug_consultadje.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def debug_consultadje():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("🌐 Acessando https://www3.tjrj.jus.br/consultadje/")
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(5)
        
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
        
        pdf_links = []
        for link in links[:20]:  # Mostra os primeiros 20
            href = link.get_attribute("href") or ""
            text = link.text.strip()
            if ".pdf" in href.lower():
                pdf_links.append((text, href))
                print(f"📄 PDF: {text} -> {href}")
        
        print(f"\n📊 PDFs encontrados: {len(pdf_links)}")
        
        # Tenta encontrar a data de hoje
        from datetime import date
        hoje = date.today().strftime("%d/%m/%Y")
        print(f"📅 Procurando data: {hoje}")
        
        elementos_data = driver.find_elements(By.XPATH, f"//*[contains(text(), '{hoje}')]")
        print(f"📆 Elementos com data de hoje: {len(elementos_data)}")
        
        for elem in elementos_data[:5]:
            print(f"   • {elem.text}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_consultadje()
