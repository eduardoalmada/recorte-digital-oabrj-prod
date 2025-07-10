from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    print("📄 Variável DATABASE_URL do os.environ:", os.environ.get("DATABASE_URL"))

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    print("📦 Banco configurado:", app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    migrate.init_app(app, db)

    from app.models import Advogado, Publicacao

    @app.route("/importar_advogados")
    def importar_advogados():
        if request.args.get("key") != os.getenv("IMPORT_KEY"):
            return "🔒 Acesso não autorizado", 403

        import csv

        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'lista-adv-oab-geral.csv')

        try:
            with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                count = 0
                for row in reader:
                    advogado = Advogado(
                        nome_completo=row['nome_completo'].strip(),
                        numero_oab=row['numero_oab'].strip(),
                        whatsapp=row.get('whatsapp', '').strip(),
                        email=row.get('email', '').strip()
                    )
                    db.session.add(advogado)
                    count += 1
                db.session.commit()
            return f"✅ {count} advogados importados com sucesso!"
        except Exception as e:
            return f"❌ Erro ao importar: {str(e)}", 500

    @app.route("/")
    def index():
        return "✅ Recorte Digital OABRJ em produção."

    return app
