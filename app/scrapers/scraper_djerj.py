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

response = requests.get(url, params=params)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")

    # Aqui você pode ajustar para encontrar onde estão os nomes dos advogados ou decisões
    for div in soup.find_all("div", class_="ementa"):
        print("📌 Publicação encontrada:")
        print(div.get_text(strip=True))
else:
    print(f"❌ Erro ao acessar o DJERJ: {response.status_code}")
