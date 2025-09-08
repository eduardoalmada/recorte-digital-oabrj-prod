import os
import sys
from flask import Flask, jsonify
from datetime import datetime

# ✅ 1. IMPORTAÇÃO E INSTÂNCIA DA APP FLASK
# O PYTHONPATH é handled pelo Dockerfile, esta parte é opcional
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from app import create_app
from app.routes.webhook import webhook_bp
from app.tasks import test_scraper_task, tarefa_buscar_publicacoes

# 2. Crie o app
app = create_app()

# 3. Defina as rotas
@app.route('/healthcheck')
def healthcheck():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ✅ ROTA PARA TESTAR O SCRAPER: AGORA DISPARA UMA TAREFA CELERY
@app.route('/test-scraper', methods=['GET'])
def test_scraper():
    """
    Dispara uma tarefa assíncrona para testar o scraper no Celery Worker.
    """
    task = test_scraper_task.delay()
    return jsonify({
        'status': 'success',
        'message': 'Tarefa de teste do scraper foi iniciada',
        'task_id': task.id,
        'task_status': 'PENDING'
    }), 200

# ✅ ROTA PARA DISPARAR A TAREFA PRINCIPAL DO SCRAPER
@app.route('/webhook/iniciar-scraper', methods=['POST'])
def iniciar_scraper_webhook():
    """
    Webhook para iniciar a tarefa principal de busca de publicações.
    """
    task = tarefa_buscar_publicacoes.delay()
    return jsonify({
        "status": "success",
        "message": "Tarefa de scraper principal foi iniciada",
        "task_id": task.id
    }), 202 # HTTP 202 indica que a requisição foi aceita para processamento

# 4. Registre blueprints
app.register_blueprint(webhook_bp, url_prefix="/webhook")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
