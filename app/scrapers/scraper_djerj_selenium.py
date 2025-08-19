import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
import unicodedata

from app import create_app, db
from app.models import Advogado, Publicacao

app = create_app()


def configurar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Novo modo headless
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = "/usr/bin/google-chrome"  # Chrome dentro do container

    return webdriver.Chrome(
        executable_path="/usr/local/bin/chromedriver",
        options=options
    )


def normalizar_texto(texto: str) -> str:
    """Remove acentos, coloca em maiúsculas e tira espaços extras."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.upper().strip()


def buscar_publicacoes_djerj():
    hoje = datetime.now().strftime("%d/%m/%Y")
    url = f"https://www3.tjrj.jus.br/consultadje/ConsultaPagina?cdCaderno=10&cdSecao=1&dataPublicacao={hoje}&cdDiario=1&pagina=1"

    driver = configurar_driver()
    driver.get(url)
    time.sleep(3)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    driver.quit()

    textos = [div.get_text(strip=True) for div in soup.find_all("div", class_="ementa")]
    print(f"📄 Total de publicações capturadas hoje: {len(textos)}")
    return textos


def enviar_mensagem_whatsapp(numero, titulo, link, nome_advogado):
    url = "https://oabrj.uzapi.com.br:3333/sendText"

    headers = {
        "Content-Type": "application/json",
        "sessionkey": "oab"
    }

    payload = {
        "session": "oab",
        "number": numero,
        "text": f"Olá {nome_advogado}, encontramos uma publicação com seu nome: *{titulo}*\nAcesse o Diário Oficial: {link}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"📤 Envio status: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp: {e}")
        return False


def processar_publicacoes_djerj():
    with app.app_context():
        advogados = Advogado.query.all()
        texto_publicacoes = buscar_publicacoes_djerj()

        print(f"👩‍⚖️ Total de advogados carregados do banco: {len(advogados)}")

        total_novas = 0

        for advogado in advogados:
            nome_normalizado = normalizar_texto(advogado.nome_completo)

            for texto in texto_publicacoes:
                texto_normalizado = normalizar_texto(texto)

                if nome_normalizado in texto_normalizado:
                    print(f"✅ Match encontrado: {advogado.nome_completo}")

                    if Publicacao.query.filter_by(titulo=texto[:100]).first():
                        print("⚠️ Publicação já existe, ignorando...")
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
        print(f"📌 {total_novas} novas publicações salvas no banco.")


if __name__ == "__main__":
    processar_publicacoes_djerj()
