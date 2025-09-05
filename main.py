import os
import sys
from flask import Flask, jsonify
from datetime import datetime

# ✅ 1. PYTHONPATH primeiro
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
print(f"📁 Diretório atual adicionado ao PYTHONPATH: {current_dir}")

# ✅ 2. DEFINA a função create_chrome_driver ANTES de importar webhook_bp
def create_chrome_driver():
    """
    Cria e retorna uma instância do Chrome WebDriver configurada
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument(f'--user-data-dir=/tmp/chrome-profile-{os.getpid()}')  # ✅ ÚNICO POR PROCESSO
    options.add_argument('--remote-debugging-port=0')
    options.binary_location = '/usr/bin/google-chrome'
    
    driver = webdriver.Chrome(options=options)
    return driver

# ✅ 3. AGORA importe os módulos que podem usar a função
from app import create_app
from app.routes.webhook import webhook_bp

# 4. Crie o app
app = create_app()

# 5. Defina as rotas
@app.route('/healthcheck')
def healthcheck():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/test-scraper')
def test_scraper():
    """
    Rota para testar se o Chrome e Selenium estão funcionando
    """
    try:
        driver = create_chrome_driver()
        driver.get('https://httpbin.org/html')
        title = driver.title
        driver.quit()
        return jsonify({
            'status': 'success', 
            'message': 'Scraper funcionando!',
            'title': title
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro no scraper: {str(e)}'
        }), 500

# 6. Registre blueprints
app.register_blueprint(webhook_bp, url_prefix="/webhook")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
