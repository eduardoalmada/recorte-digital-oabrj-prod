from flask import Flask, jsonify
from app import create_app
from app.routes.webhook import webhook_bp
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ✅ FUNÇÃO PARA CRIAR DRIVER DO CHROME (adicionada aqui)
def create_chrome_driver():
    """
    Cria e retorna uma instância do Chrome WebDriver configurada para o ambiente Render
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--user-data-dir=/tmp/chrome-profile')
    options.add_argument('--remote-debugging-port=0')
    options.binary_location = '/usr/bin/google-chrome'  # Caminho correto no Render
    
    driver = webdriver.Chrome(options=options)
    return driver

# 1. Crie o app PRIMEIRO
app = create_app()

# 2. Depois adicione as rotas
@app.route('/healthcheck')
def healthcheck():
    # Use jsonify para garantir o formato e Content-Type corretos
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ✅ EXEMPLO: Rota de teste do scraper (adicione se necessário)
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

# 3. Depois registre blueprints
app.register_blueprint(webhook_bp, url_prefix="/webhook")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
