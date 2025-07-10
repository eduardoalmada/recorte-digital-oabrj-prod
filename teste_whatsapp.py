import requests

def enviar_mensagem_whatsapp(numero, titulo, descricao, link):
    url = "https://oabrj.uzapi.com.br:3333/sendLink"

    headers = {
        "Content-Type": "application/json",
        "sessionkey": "oab"  # <- CORRETO: header, não query param
    }

    payload = {
        "session": "oab",
        "number": numero,
        "text": descricao,
        "url": link,
        "title": titulo
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("✅ Mensagem enviada com sucesso!")
        print(response.json())
    else:
        print("❌ Falha ao enviar mensagem:")
        print(response.status_code, response.text)

# Exemplo de teste
enviar_mensagem_whatsapp(
    numero="5521986727627",
    titulo="🚨 Nova publicação",
    descricao="Seu nome foi citado no Diário Oficial. Veja mais detalhes no link abaixo.",
    link="https://www3.tjrj.jus.br/consultadje/"
)
