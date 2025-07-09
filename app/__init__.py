from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    @app.route("/initdb")
def init_db():
    from app.models import db
    db.create_all()
    return "✅ Tabelas criadas com sucesso!"

    
    @app.route("/")
    def index():
        return "✅ Recorte Digital OABRJ em produção."

    # Importa os modelos
    from app import models

    return app
