from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Configurações do Chrome em modo headless
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Inicializa o Chrome com o WebDriver Manager
driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

try:
    # Acessa o site do DJERJ
    driver.get("https://www3.tjrj.jus.br/consultadje/")

    # Aguarda o carregamento da página
    time.sleep(3)

    # Captura o HTML completo da página
    html = driver.page_source

    # Processa com BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Extrai publicações, se houver
    print("📄 Resultados encontrados:")
    for div in soup.find_all("div", class_="ementa"):
        print("📌", div.get_text(strip=True))

except Exception as e:
    print(f"❌ Erro ao executar o scraper: {e}")

finally:
    driver.quit()
