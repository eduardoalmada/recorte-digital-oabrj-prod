import os
import sys
from flask import Flask, jsonify
from datetime import datetime

# =========================
# 1. IMPORTAÇÃO E PYTHONPATH
# =========================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# =========================
# 2. IMPORTE A INSTÂNCIA DO CELERY
# =========================
# Importa a instância configurada do celery_worker.py (na raiz)
from celery_worker import celery_app  # ✅ Agora importa do arquivo correto

# =========================
# 4. IMPORTAÇÕES DO SEU APP
# =========================
from app import create_app
from app.routes.webhook import webhook_bp
from app.tasks import tarefa_buscar_publicacoes

# =========================
# 5. CRIAÇÃO DO FLASK APP
# =========================
app = create_app()

# =========================
# 6. ROTAS
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
# 7. BLUEPRINTS
# =========================
app.register_blueprint(webhook_bp, url_prefix="/webhook")

# =========================
# 8. EXECUÇÃO LOCAL
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
