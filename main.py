from flask import Flask, jsonify
from app import create_app
from app.routes.webhook import webhook_bp
from datetime import datetime

# 1. Crie o app PRIMEIRO
app = create_app()

# 2. Depois adicione as rotas
@app.route('/healthcheck')
def healthcheck():
    # Use jsonify para garantir o formato e Content-Type corretos
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# 3. Depois registre blueprints
app.register_blueprint(webhook_bp, url_prefix="/webhook")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
