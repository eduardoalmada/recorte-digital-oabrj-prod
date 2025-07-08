from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "✅ API do Recorte Digital OABRJ está rodando!"

    @app.route("/forcar-busca")
    def forcar_busca():
        tarefa_buscar_publicacoes.delay()
        return "🔍 Tarefa de busca forçada enviada para o worker."

    return app
