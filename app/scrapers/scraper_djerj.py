import requests
from bs4 import BeautifulSoup

url = "https://www3.tjrj.jus.br/consultadje/ConsultaPagina"
params = {
    "cdCaderno": "10",  # Caderno I
    "cdSecao": "1",     # Seção I
    "dataPublicacao": "11/07/2025",  # Data da edição do DJERJ
    "cdDiario": "1",    # Diário da Justiça Eletrônico
    "pagina": "1"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www3.tjrj.jus.br/consultadje/"
}

response = requests.get(url, params=params, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "lxml")

    for div in soup.find_all("div", class_="ementa"):
        print("📌 Publicação encontrada:")
        print(div.get_text(strip=True))
else:
    print(f"❌ Erro ao acessar o DJERJ: {response.status_code}")
