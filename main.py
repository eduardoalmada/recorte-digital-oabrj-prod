from flask import Flask
from app import create_app
from app.routes.webhook import webhook_bp  # importa o blueprint

app = create_app()

# registra o blueprint do webhook
app.register_blueprint(webhook_bp, url_prefix="/webhook")

if __name__ == "__main__":
    # Em produção use Gunicorn (Render já faz). Local: python main.py
    app.run(host="0.0.0.0", port=5000, debug=False)
