import os
import sys
from flask import Flask, jsonify
from datetime import datetime
from celery import Celery  # Importação essencial

# =========================
# 1. IMPORTAÇÃO E PYTHONPATH
# =========================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# =========================
# 2. INICIALIZAÇÃO DO CELERY (GLOBAL)
# =========================
# Esta instância será acessível tanto pelo web service quanto pelo worker
celery_app = Celery(
    "recorte_digital",
    broker=os.getenv("REDIS_BROKER_URL"),
    backend=os.getenv("REDIS_BROKER_URL"),
    include=['app.tasks']
)

# Força a conexão com o Redis na inicialização do web service
# Isso evita o ConnectionRefusedError quando tentar enviar tarefas
celery_app.connection()

# =========================
# 3. IMPORTAÇÕES APÓS O CELERY
# =========================
from app import create_app
from app.routes.webhook import webhook_bp
from app.tasks import test_scraper_task, tarefa_buscar_publicacoes

# =========================
# 4. CRIAÇÃO DO FLASK APP
# =========================
app = create_app()

# =========================
# 5. ROTAS
# =========================
@app.route('/healthcheck')
def healthcheck():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

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
    }), 202

# =========================
# 6. BLUEPRINTS
# =========================
app.register_blueprint(webhook_bp, url_prefix="/webhook")

# =========================
# 7. EXECUÇÃO LOCAL
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
