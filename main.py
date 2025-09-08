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
from celery_worker import celery_app  # ✅ Importa do arquivo correto

# =========================
# 3. IMPORTAÇÕES DO SEU APP
# =========================
from app import create_app
from app.routes.webhook import webhook_bp
from app.tasks import tarefa_buscar_publicacoes  # ✅ APENAS TASK EXISTENTE

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
    Dispara a tarefa PRINCIPAL para teste real.
    """
    task = tarefa_buscar_publicacoes.delay()  # ✅ USA TASK EXISTENTE
    return jsonify({
        'status': 'success',
        'message': 'Tarefa de scraper principal iniciada (teste real)',
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
