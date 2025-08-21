from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def main():
    print("🌐 Acessando consultadje...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # 🚀 Deixa o Selenium achar o chromedriver sozinho
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(3)

        print("✅ Página carregada:", driver.title)

        # exemplo de debug: pegar o HTML inicial
        print(driver.page_source[:500])  # só primeiros 500 chars

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
