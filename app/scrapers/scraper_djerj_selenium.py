import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests

from app import create_app, db
from app.models import Advogado, Publicacao

app = create_app()

def configurar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.binary_location = "/usr/bin/google-chrome"

    return webdriver.Chrome(options=options)

def buscar_publicacoes_djerj():
    hoje = datetime.now().strftime("%d/%m/%Y")
    url = f"https://www3.tjrj.jus.br/consultadje/ConsultaPagina?cdCaderno=10&cdSecao=1&dataPublicacao={hoje}&cdDiario=1&pagina=1"
    driver = configurar_driver()
    driver.get(url)
    time.sleep(3)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    driver.quit()
    return [div.get_text(strip=True) for div in soup.find_all("div", class_="ementa")]


def enviar_mensagem_whatsapp(numero, titulo, link, nome_advogado):
    url = "https://oabrj.uzapi.com.br:3333/sendText"  # Usar endpoint correto

    headers = {
        "Content-Type": "application/json",
        "sessionkey": "oab"  # Agora no header
    }

    payload = {
        "session": "oab",
        "number": numero,
        "text": f"Olá {nome_advogado}, encontramos uma publicação com seu nome: *{titulo}*\nAcesse o Diário Oficial: {link}"
    }

    response = requests.post(url, json=payload, headers=headers)
    print(f"📤 Envio status: {response.status_code} - {response.text}")
    return response.status_code == 200


def processar_publicacoes_djerj():
    with app.app_context():
        advogados = Advogado.query.all()
        texto_publicacoes = buscar_publicacoes_djerj()
        total_novas = 0

        for advogado in advogados:
            for texto in texto_publicacoes:
                if advogado.nome_completo.upper() in texto.upper():
                    if Publicacao.query.filter_by(titulo=texto).first():
                        continue

                    nova_pub = Publicacao(
                        advogado_id=advogado.id,
                        titulo=texto[:100],
                        descricao=texto,
                        data=datetime.now(),
                        link="https://www3.tjrj.jus.br/consultadje/"
                    )

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
    processar_publicacoes_djerj()
