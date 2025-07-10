import requests
from datetime import datetime
from app import create_app, db
from app.models import Advogado, Publicacao
from app.config import Config

app = create_app()

# Função para enviar mensagem via WhatsApp usando a UZAPI
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

# Busca no DataJud por nome
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

# Processa e salva publicações no banco
def processar_publicacoes():
    with app.app_context():
        advogados = Advogado.query.all()
        total_novas = 0

        for advogado in advogados:
            resultados = buscar_publicacoes_por_nome(advogado.nome_completo)
            print(f"🔍 Buscando publicações para {advogado.nome_completo}")
            print(f"🔢 Encontrados {len(resultados)} resultados")

            for item in resultados:
                doc = item["_source"]
                link = "https://www3.tjrj.jus.br/consultadje/"

                # Verifica se já existe publicação igual
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

                # Envia mensagem via WhatsApp se houver número
                if advogado.whatsapp:
                    enviado = enviar_mensagem_whatsapp(
                        numero=advogado.whatsapp,
                        titulo=nova_pub.titulo,
                        link=nova_pub.link,
                        nome_advogado=advogado.nome_completo.split()[0]
                    )
                    if enviado:
                        nova_pub.notificado = True

                db.session.add(nova_pub)
                total_novas += 1

        db.session.commit()
        print(f"✅ {total_novas} novas publicações salvas no banco.")

if __name__ == "__main__":
    processar_publicacoes()
