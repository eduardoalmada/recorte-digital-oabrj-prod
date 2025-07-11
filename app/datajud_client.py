import requests
from datetime import datetime
from app import create_app, db
from app.models import Advogado, Publicacao
from app.config import Config

app = create_app()

# Envia mensagem via WhatsApp
def enviar_mensagem_whatsapp(numero, titulo, link, nome_advogado):
    url = "https://oabrj.uzapi.com.br:3333/sendLink"

    payload = {
        "session": "oab",
        "sessionkey": "oab",
        "number": numero,
        "text": f"Olá {nome_advogado}, encontramos uma publicação com seu nome: *{titulo}*",
        "linkUrl": link,
        "linkText": "Clique aqui para ver no Diário Oficial"
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print(f"📨 Mensagem enviada com sucesso para {numero}")
        return True
    else:
        print(f"❌ Erro ao enviar para {numero}: {response.status_code} - {response.text}")
        return False

# Busca usando nome e opcionalmente OAB
def buscar_publicacoes_datajud(nome_completo, numero_oab=None):
    headers = {
        "Authorization": f"APIKey {Config.DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Usa multi_match com nome + match OAB se disponível
    must_clauses = [
        {
            "multi_match": {
                "query": nome_completo,
                "type": "phrase",
                "fields": ["nome_parte", "texto_decisao", "nome_advogado", "outros_participantes"]
            }
        }
    ]

    if numero_oab:
        must_clauses.append({
            "match_phrase": {
                "numero_oab": numero_oab
            }
        })

    payload = {
        "query": {
            "bool": {
                "must": must_clauses
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

# Processa só o advogado Eduardo Pacheco
def processar_publicacoes():
    with app.app_context():
        eduardo = Advogado.query.filter(Advogado.nome_completo.ilike("%EDUARDO PACHECO DE CASTRO%")).first()

        if not eduardo:
            print("⚠️ Advogado Eduardo não encontrado no banco.")
            return

        resultados = buscar_publicacoes_datajud(eduardo.nome_completo, eduardo.numero_oab)
        print(f"🔍 Buscando publicações para {eduardo.nome_completo}")
        print(f"🔢 Encontrados {len(resultados)} resultados")

        total_novas = 0
        for item in resultados:
            doc = item["_source"]
            link = "https://www3.tjrj.jus.br/consultadje/"

            # Evita duplicata
            existe = Publicacao.query.filter_by(titulo=doc.get('assunto'), link=link).first()
            if existe:
                continue

            nova_pub = Publicacao(
                advogado_id=eduardo.id,
                titulo=doc.get("assunto", "Sem título"),
                descricao=doc.get("texto_decisao", "Sem descrição."),
                data=datetime.strptime(doc.get("data_movimento"), "%Y-%m-%d"),
                link=link
            )

            if eduardo.whatsapp:
                enviado = enviar_mensagem_whatsapp(
                    numero=eduardo.whatsapp,
                    titulo=nova_pub.titulo,
                    link=nova_pub.link,
                    nome_advogado=eduardo.nome_completo.split()[0]
                )
                if enviado:
                    nova_pub.notificado = True

            db.session.add(nova_pub)
            total_novas += 1

        db.session.commit()
        print(f"✅ {total_novas} novas publicações salvas no banco.")

if __name__ == "__main__":
    processar_publicacoes()
