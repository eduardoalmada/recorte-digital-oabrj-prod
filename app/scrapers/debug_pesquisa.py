import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    print("🌐 Acessando consultadje...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,1024")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(3)
        print("✅ Título:", driver.title)
        print("🧩 Tem body?", bool(driver.find_elements("tag name", "body")))
        print("🔗 Âncoras:", len(driver.find_elements("tag name", "a")))
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
