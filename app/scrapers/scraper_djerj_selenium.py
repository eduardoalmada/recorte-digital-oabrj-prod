import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

from app import create_app, db
from app.models import DiarioOficial, Publicacao, Advogado

# Configuração do Selenium (modo headless)
def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    return driver

def executar_scraper():
    app = create_app()

    # Garantir que o acesso ao banco está dentro do contexto do Flask
    with app.app_context():
        hoje = datetime.now().date()
        print(f"📅 Rodando scraper para o dia {hoje}")

        # Evitar duplicação
        if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
            print(f"📌 Diário Oficial de {hoje} já armazenado.")
            return

        driver = iniciar_driver()
        try:
            url = "https://www3.tjrj.jus.br/consultadje/"
            driver.get(url)
            time.sleep(5)  # espera a página carregar

            # Pega o HTML e analisa
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Exemplo simples: busca todas as divs de publicações
            publicacoes_html = soup.find_all("div", class_="publicacao")

            if not publicacoes_html:
                print("⚠️ Nenhuma publicação encontrada no site.")
                return

            # Cria o registro do Diário de hoje
            diario = DiarioOficial(data_publicacao=hoje)
            db.session.add(diario)
            db.session.commit()

            # Percorre e salva publicações
            for bloco in publicacoes_html:
                texto = bloco.get_text(separator=" ", strip=True)

                publicacao = Publicacao(
                    diario_id=diario.id,
                    conteudo=texto,
                )
                db.session.add(publicacao)

                # 🔎 Busca nomes de advogados no conteúdo
                advogados = Advogado.query.all()
                for adv in advogados:
                    if adv.nome_completo and adv.nome_completo.upper() in texto.upper():
                        print(f"✅ Nome encontrado: {adv.nome_completo}")
                        publicacao.advogados.append(adv)

            db.session.commit()
            print(f"📦 Diário de {hoje} salvo com {len(publicacoes_html)} publicações.")

        finally:
            driver.quit()


if __name__ == "__main__":
    executar_scraper()
