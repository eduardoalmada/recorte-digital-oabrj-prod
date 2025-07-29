import requests
from datetime import datetime
from app.config import Config

def buscar_publicacoes():
    headers = {
        "Authorization": f"APIKey {Config.DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Exemplo de um nome a ser pesquisado — futuramente será uma lista vinda do banco
    nomes_para_busca = [
        {"nome": "Daniel Soares Motta", "oab": "123456"},
        {"nome": "Ivan dos Santos Gonçalves", "oab": "654321"},
        {"nome": "Leandro Terra Oliveira Comyn do Amaral", "oab": "789101"}
    ]

    for advogado in nomes_para_busca:
        payload = {
            "query": {
                "bool": {
                    "must": [
                        {"match_phrase": {"nome_parte": advogado["nome"]}},
                        {"match_phrase": {"numero_oab": advogado["oab"]}}
                    ]
                }
            }
        }

        response = requests.post(Config.DATAJUD_API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            dados = response.json()
            resultados = dados.get("hits", {}).get("hits", [])

            if resultados:
                for item in resultados:
                    doc = item["_source"]
                    print("🚨 Nova publicação encontrada!")
                    print(f"Título: {doc.get('assunto')}")
                    print(f"Link: https://www3.tjrj.jus.br/consultadje/")
                    print(f"Data: {doc.get('data_movimento')}")
                    print(f"Descrição: {doc.get('texto_decisao', 'Sem resumo.')}")
                    print("--------")
