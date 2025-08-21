import os
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://www3.tjrj.jus.br/consultadje/"
OUTPUT_DIR = Path("/app/debug_screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def tirar_screenshot(driver, nome):
    path = OUTPUT_DIR / f"{nome}.png"
    driver.save_screenshot(str(path))
    print(f"📸 Screenshot salva: {path}")

def salvar_html(driver, nome):
    path = OUTPUT_DIR / f"{nome}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"📄 HTML salvo: {path}")

def listar_iframes(driver):
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"🖼️ {len(iframes)} iframe(s) encontrados:")
    for i, iframe in enumerate(iframes):
        print(f"   [{i}] name={iframe.get_attribute('name')} id={iframe.get_attribute('id')} src={iframe.get_attribute('src')}")

def main():
    print("🌐 Acessando consultadje...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,1024")

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(URL)
    time.sleep(3)
    tirar_screenshot(driver, "01_inicio")
    salvar_html(driver, "01_inicio")
    listar_iframes(driver)

    try:
        # tenta achar qualquer botão/aba com o texto "Pesquisa"
        abas = driver.find_elements(By.XPATH, "//*[contains(text(), 'Pesquisa')]")
        print(f"🔎 Encontradas {len(abas)} ocorrências de 'Pesquisa'")
        for i, aba in enumerate(abas):
            print(f"   [{i}] tag={aba.tag_name} id={aba.get_attribute('id')} class={aba.get_attribute('class')}")
        
        if abas:
            print("👉 Tentando clicar na primeira ocorrência...")
            driver.execute_script("arguments[0].click();", abas[0])
            time.sleep(3)
            tirar_screenshot(driver, "02_pos_clique")
            salvar_html(driver, "02_pos_clique")
        else:
            print("❌ Nenhuma aba com texto 'Pesquisa' encontrada")
    except Exception as e:
        print(f"⚠️ Erro ao procurar/clicar na aba Pesquisa: {e}")

    driver.quit()
    print("✅ Debug finalizado")

if __name__ == "__main__":
    main()
