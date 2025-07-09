from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    print("📄 Variável DATABASE_URL do os.environ:", os.environ.get("DATABASE_URL"))

    app = Flask(__name__)  # ✅ Corrigido aqui
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print("📦 Banco configurado:", app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    migrate.init_app(app, db)

    # Importa os modelos
    from app.models import Advogado,Publicacao

    @app.route("/")
    def index():
        return "✅ Recorte Digital OABRJ em produção."

    return app
