import requests

def enviar_mensagem_whatsapp(numero, titulo, descricao, link):
    url = "https://oabrj.uzapi.com.br:3333/sendLink?sessionkey=oab"
    
    payload = {
        "session": "oab",  # nome da sessão que você me passou
        "number": numero,
        "text": descricao,
        "url": link,
        "title": titulo
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print("✅ Mensagem enviada com sucesso!")
        print(response.json())
    else:
        print("❌ Falha ao enviar mensagem:")
        print(response.status_code, response.text)

# Exemplo de teste
enviar_mensagem_whatsapp(
    numero="5521987654321",
    titulo="🚨 Nova publicação",
    descricao="Seu nome foi citado no Diário Oficial. Veja mais detalhes no link abaixo.",
    link="https://www3.tjrj.jus.br/consultadje/"
)
