from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "✅ Recorte Digital OABRJ em produção."

    return app
