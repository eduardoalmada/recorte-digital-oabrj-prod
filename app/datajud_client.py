import requests
from datetime import datetime
from app import create_app, db
from app.models import Advogado, Publicacao
from app.config import Config

app = create_app()

def buscar_publicacoes_por_nome(nome_completo):
    headers = {
        "Authorization": f"APIKey {Config.DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": {
            "match_phrase": {
                "nome_parte": nome_completo
            }
        },
        "size": 100
    }

    response = requests.post(Config.DATAJUD_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get("hits", {}).get("hits", [])
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")
        return []

def processar_publicacoes():
    with app.app_context():
        advogados = Advogado.query.all()
        total_novas = 0

        for advogado in advogados:
            resultados = buscar_publicacoes_por_nome(advogado.nome_completo)

            for item in resultados:
                doc = item["_source"]

                # Identificador único (pode mudar conforme DataJud)
                link = "https://www3.tjrj.jus.br/consultadje/"

                # Verifica se já existe publicação igual (evita duplicatas)
                existe = Publicacao.query.filter_by(titulo=doc.get('assunto'), link=link).first()
                if existe:
                    continue

                nova_pub = Publicacao(
                    advogado_id=advogado.id,
                    titulo=doc.get("assunto", "Sem título"),
                    descricao=doc.get("texto_decisao", "Sem descrição."),
                    data=datetime.strptime(doc.get("data_movimento"), "%Y-%m-%d"),
                    link=link
                )

                db.session.add(nova_pub)
                total_novas += 1

        db.session.commit()
        print(f"✅ {total_novas} novas publicações salvas no banco.")

if __name__ == "__main__":
    processar_publicacoes()
