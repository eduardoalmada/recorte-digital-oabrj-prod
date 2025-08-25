# app/scrapers/scraper_completo_djerj.py

import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import re
from pdfminer.high_level import extract_text
import unicodedata

from app import db, create_app
from app.models import DiarioOficial, Advogado, AdvogadoPublicacao

# ========== FUNÇÕES EXISTENTES (inalteradas para o teste) ==========

def normalizar_texto(texto):
    """Remove acentos e converte para maiúsculas para melhor busca"""
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto

def extrair_texto_pdf(caminho_pdf):
    try:
        texto = extract_text(caminho_pdf)
        print(f"📄 Texto extraído: {len(texto)} caracteres")
        return texto
    except Exception as e:
        print(f"❌ Erro ao extrair texto: {e}")
        return ""

# ========== FUNÇÃO DE ENVIO AGORA CORRETA ==========

def enviar_whatsapp(telefone, mensagem):
    """Envia mensagem pelo WhatsApp API da OABRJ"""
    if not telefone:
        print("⚠️ Número de WhatsApp não informado")
        return
    
    try:
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        
        headers = {
            "Content-Type": "application/json",
            "sessionkey": "oab"
        }
        
        payload = {
            "session": "oab",
            "number": telefone,
            "text": mensagem,
        }
        
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            print(f"✅ Mensagem enviada para {telefone}")
        else:
            print(f"❌ Falha ao enviar mensagem ({r.status_code}): {r.text}")
            print(f"Resposta da API: {r.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp: {e}")

def buscar_advogados_no_texto(texto, advogados):
    """Busca advogados no texto do diário"""
    texto_normalizado = normalizar_texto(texto)
    encontrados = []
    
    for advogado in advogados:
        nome_normalizado = normalizar_texto(advogado.nome_completo)
        
        if nome_normalizado in texto_normalizado:
            qtd_mencoes = texto_normalizado.count(nome_normalizado)
            encontrados.append((advogado, qtd_mencoes))
            print(f"✅ {advogado.nome_completo}: {qtd_mencoes} menções")
    
    return encontrados

# ========== FUNÇÃO PRINCIPAL DE TESTE ==========

def executar_teste_notificacao_djerj():
    """
    Função de teste para notificação de advogados com base em um PDF
    existente no banco de dados.
    """
    print("📋 Executando teste de notificação...")

    # Passo 1: Buscar o último PDF do diário no banco de dados
    diario = DiarioOficial.query.order_by(DiarioOficial.data_publicacao.desc()).first()

    if not diario or not os.path.exists(diario.arquivo_pdf):
        print("❌ Nenhum PDF recente encontrado no banco de dados ou o arquivo não existe.")
        return

    caminho_pdf = diario.arquivo_pdf
    data_publicacao = diario.data_publicacao
    print(f"✅ PDF encontrado: {caminho_pdf} da data {data_publicacao.strftime('%d/%m/%Y')}")

    # Passo 2: Extrair o texto do PDF
    texto = extrair_texto_pdf(caminho_pdf)
    if not texto:
        print("❌ Não foi possível extrair texto do PDF.")
        return

    # Passo 3: Buscar advogados cadastrados no banco de dados
    advogados = Advogado.query.all()
    print(f"👨‍💼 Advogados no banco: {len(advogados)}")

    # Passo 4: Procurar advogados no texto
    advogados_encontrados = buscar_advogados_no_texto(texto, advogados)
    
    if not advogados_encontrados:
        print("❌ Nenhum advogado encontrado nas publicações de hoje.")
        return

    advogados_notificados = 0

    # Passo 5: Enviar mensagem para cada advogado encontrado
    for advogado, qtd_mencoes in advogados_encontrados:
        mensagem = (
            f"Olá, {advogado.nome_completo}. "
            f"O Recorte Digital da OABRJ encontrou {qtd_mencoes} "
            f"menções em seu nome no Diário da Justiça Eletrônico do Estado do Rio de Janeiro "
            f"({data_publicacao.strftime('%d/%m/%Y')})."
        )
        
        # Adiciona o link da publicação
        link_diario = f"\nAcesse o Diário completo aqui: https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data_publicacao.strftime('%d/%m/%Y')}"
        mensagem_final = mensagem + link_diario

        enviar_whatsapp(advogado.whatsapp, mensagem_final)
        advogados_notificados += 1

    print(f"✅ Teste de notificação concluído:")
    print(f"   - Advogados encontrados: {len(advogados_encontrados)}")
    print(f"   - Notificações enviadas: {advogados_notificados}")


# ========== MAIN ==========

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Chame a nova função de teste aqui
        executar_teste_notificacao_djerj()
