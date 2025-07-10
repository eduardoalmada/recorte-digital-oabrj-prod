import requests
from datetime import datetime
from app import create_app, db
from app.models import Advogado, Publicacao
from app.config import Config
import os

app = create_app()

def enviar_whatsapp(telefone, mensagem):
    url = os.getenv("WHATSAPP_API_URL")
    if not url:
        print("❌ WHATSAPP_API_URL não configurado.")
        return

    payload = {
        "phone": telefone,
        "message": mensagem
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"📲 Mensagem enviada para {telefone}")
        else:
            print(f"❌ Erro ao enviar para {telefone}: {response.text}")
    except Exception as e:
        print(f"⚠️ Erro inesperado no envio de WhatsApp: {str(e)}")


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
        print(f"❌ Erro {response.status_code} ao buscar '{nome_completo}': {response.text}")
        return []


def processar_publicacoes():
    with app.app_context():
        advogados = Advogado.query.all()
        total_novas = 0

        for advogado in advogados:
            resultados = buscar_publicacoes_por_nome(advogado.nome_completo)

            for item in resultados:
                doc = item["_source"]
                link = "https://www3.tjrj.jus.br/consultadje/"  # link fixo

                # Evita duplicatas
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

                # Envia WhatsApp
                if advogado.whatsapp:
                    mensagem = (
                        f"📢 Olá {advogado.nome_completo}, encontramos uma nova publicação em seu nome no DJe-RJ.\n\n"
                        f"📌 Assunto: {nova_pub.titulo}\n"
                        f"📅 Data: {nova_pub.data.strftime('%d/%m/%Y')}\n"
                        f"🔗 Link: {nova_pub.link}"
                    )
                    enviar_whatsapp(advogado.whatsapp, mensagem)

        db.session.commit()
        print(f"✅ {total_novas} novas publicações salvas no banco.")


if __name__ == "__main__":
    processar_publicacoes()
