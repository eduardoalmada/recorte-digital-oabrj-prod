import requests
from bs4 import BeautifulSoup

def buscar_djerj():
    url = "https://www3.tjrj.jus.br/consultadje/ConsultaPagina"
    params = {
        "cdCaderno": "10",  # Caderno I
        "cdSecao": "1",     # Seção I
        "dataPublicacao": "11/07/2025",  # Data da edição do DJERJ
        "cdDiario": "1",    # Diário da Justiça Eletrônico
        "pagina": "1"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")

        publicacoes = soup.find_all("div", class_="ementa")

        if not publicacoes:
            print("⚠️ Nenhuma publicação encontrada para os critérios informados.")
        else:
            for div in publicacoes:
                print("📌 Publicação encontrada:")
                print(div.get_text(strip=True))
    else:
        print(f"❌ Erro ao acessar o DJERJ: {response.status_code}")

if __name__ == "__main__":
    buscar_djerj()
