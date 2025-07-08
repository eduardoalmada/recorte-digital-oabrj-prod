from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    @app.route("/")
    def index():
        return "✅ Recorte Digital OABRJ em produção."

    # Importa os modelos e cria as tabelas (se necessário)
    with app.app_context():
        from app import models
        db.create_all()

    return app
