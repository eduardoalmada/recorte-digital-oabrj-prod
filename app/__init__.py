from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    # 🔧 Lê de SQLALCHEMY_DATABASE_URI primeiro (Render), depois DATABASE_URL (heroku ou local)
    db_uri = os.getenv("SQLALCHEMY_DATABASE_URI") or os.getenv("DATABASE_URL")
    if not db_uri:
        raise RuntimeError("❌ Nenhuma URI de banco encontrada nas variáveis de ambiente.")

    print("📄 DATABASE_URL utilizada:", db_uri)

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print("📦 Banco configurado:", app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    migrate.init_app(app, db)

    # (continua o restante do seu código normalmente)
