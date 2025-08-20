# app/scrapers/debug_pesquisa.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from datetime import date

def debug_pesquisa():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("🌐 Acessando consultadje...")
        driver.get("https://www3.tjrj.jus.br/consultadje/")
        time.sleep(5)
        
        print("📸 Tirando screenshot da página inicial...")
        driver.save_screenshot("/tmp/consultadje_inicial.png")
        
        # Tenta encontrar a aba de pesquisa
        try:
            aba_pesquisa = driver.find_element(By.XPATH, "//a[@href='#pills-pesquisa']")
            print("✅ Encontrou aba pesquisa")
            aba_pesquisa.click()
            time.sleep(2)
        except:
            print("❌ Não encontrou aba pesquisa")
            return
        
        # Mostra todos os campos do formulário
        print("\n📋 Campos do formulário encontrados:")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        selects = driver.find_elements(By.TAG_NAME, "select")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        
        print(f"📝 Inputs: {len(inputs)}")
        for i, inp in enumerate(inputs[:10]):
            name = inp.get_attribute("name") or inp.get_attribute("id") or "sem-nome"
            print(f"   {i+1}. {name}")
        
        print(f"📝 Selects: {len(selects)}")
        print(f"📝 Buttons: {len(buttons)}")
        for btn in buttons:
            text = btn.text.strip()
            if text:
                print(f"   • {text}")
        
        # Tenta preencher data
        hoje = date.today().strftime("%d/%m/%Y")
        print(f"\n📅 Tentando preencher data: {hoje}")
        
        try:
            data_inicial = driver.find_element(By.NAME, "dataInicial")
            data_inicial.clear()
            data_inicial.send_keys(hoje)
            print("✅ Preencheu data inicial")
        except:
            print("❌ Não conseguiu preencher data inicial")
        
        # Screenshot do formulário
        driver.save_screenshot("/tmp/consultadje_formulario.png")
        print("📸 Screenshot do formulário: /tmp/consultadje_formulario.png")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_pesquisa()
