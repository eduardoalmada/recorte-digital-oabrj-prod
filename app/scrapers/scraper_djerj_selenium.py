import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests

from app import create_app, db
from app.models import Advogado, Publicacao

# Cria o app Flask e contexto do banco
app = create_app()

def configurar_driver():
    """Configura o navegador headless via Selenium"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def buscar_publicacoes_djerj():
    """Acessa o site do DJERJ via Selenium e retorna lista de textos encontrados"""
    hoje = datetime.now().strftime("%d/%m/%Y")
    url = f"https://www3.tjrj.jus.br/consultadje/ConsultaPagina?cdCaderno=10&cdSecao=1&dataPublicacao={hoje}&cdDiario=1&pagina=1"

    driver = configurar_driver()
    driver.get(url)
    time.sleep(3)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    driver.quit()

    publicacoes = []
    for div in soup.find_all("div", class_="ementa"):
        texto = div.get_text(strip=True)
        publicacoes.append(texto)
    
    return publicacoes

def enviar_mensagem_whatsapp(numero, titulo, link, nome_advogado):
    """Envia mensagem via WhatsApp usando UZAPI"""
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
    return response.status_code == 200

def processar_publicacoes_djerj():
    """Processa e envia as publicações aos advogados cadastrados"""
    with app.app_context():
        advogados = Advogado.query.all()
        texto_publicacoes = buscar_publicacoes_djerj()
        total_novas = 0

        for advogado in advogados:
            for texto in texto_publicacoes:
                if advogado.nome_completo.upper() in texto.upper():
                    # Evita duplicata
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
