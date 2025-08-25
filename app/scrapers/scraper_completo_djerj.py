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


# ========== DOWNLOAD PDF ==========

def baixar_pdf_durante_sessao(data):
    """Baixa o PDF durante a sessão do Selenium para evitar expiração"""
    print(f'🔍 Buscando PDF para {data.strftime("%d/%m/%Y")}...')

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        url = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime('%d/%m/%Y')}&caderno=E&pagina=-1"
        driver.get(url)

        time.sleep(8)  # Aumentei o tempo de espera

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for iframe in iframes:
            iframe_src = iframe.get_attribute("src") or ""

            if "pdf.aspx" in iframe_src:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(5)  # Mais tempo para o iframe carregar

                    # Tentar encontrar o link do PDF de forma mais robusta
                    iframe_html = driver.page_source
                    
                    # Procurar o PDF de múltiplas formas
                    pdf_patterns = [
                        r"filename=([^&\"']+)",
                        r"/(temp/[^\"']+\.pdf)",
                        r"openPDF\('([^']+)'\)"
                    ]
                    
                    pdf_urls = []
                    for pattern in pdf_patterns:
                        matches = re.findall(pattern, iframe_html, re.IGNORECASE)
                        pdf_urls.extend(matches)
                    
                    print(f"📝 URLs encontradas: {pdf_urls}")

                    for pdf_path in pdf_urls:
                        # Limpar o caminho
                        if pdf_path.startswith('/consultadje/temp/'):
                            pdf_path = pdf_path.replace('/consultadje/temp/', '')
                        elif pdf_path.startswith('temp/'):
                            pdf_path = pdf_path.replace('temp/', '')
                        
                        pdf_url = f"https://www3.tjrj.jus.br/consultadje/temp/{pdf_path}"
                        print(f"🎯 Tentando URL: {pdf_url}")

                        # Usar as cookies da sessão
                        cookies = driver.get_cookies()
                        session = requests.Session()

                        for cookie in cookies:
                            session.cookies.set(cookie["name"], cookie["value"])

                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "application/pdf, */*",
                            "Referer": driver.current_url,
                        }

                        try:
                            response = session.get(pdf_url, headers=headers, timeout=30)
                            print(f"📊 Status: {response.status_code}, Tamanho: {len(response.content)}")

                            if response.status_code == 200 and response.content.startswith(b"%PDF"):
                                print("✅ PDF baixado com sucesso!")
                                driver.switch_to.default_content()
                                return response.content
                            else:
                                print("❌ Não é um PDF válido")

                        except Exception as e:
                            print(f"❌ Erro ao baixar PDF: {e}")

                    driver.switch_to.default_content()

                except Exception as e:
                    print(f"❌ Erro no iframe: {e}")
                    driver.switch_to.default_content()
                    continue

        print("❌ Nenhum PDF encontrado nos iframes")
        return None

    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return None
    finally:
        driver.quit()


# ========== NORMALIZAÇÃO DE TEXTO ==========

def normalizar_texto(texto):
    """Remove acentos e converte para maiúsculas para melhor busca"""
    texto = texto.upper()
    # Remove acentos
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto


# ========== CONTAGEM DE PUBLICAÇÕES ==========

def contar_publicacoes_advogados(texto):
    """Conta quantas vezes a palavra 'ADVOGADO' aparece (estimativa de publicações)"""
    texto_normalizado = normalizar_texto(texto)
    # Conta ocorrências da palavra ADVOGADO (sem acentos)
    return texto_normalizado.count('ADVOGADO')


# ========== EXTRAÇÃO PDF ==========

def extrair_texto_pdf(caminho_pdf):
    try:
        texto = extract_text(caminho_pdf)
        print(f"📄 Texto extraído: {len(texto)} caracteres")
        return texto
    except Exception as e:
        print(f"❌ Erro ao extrair texto: {e}")
        return ""


# ========== WHATSAPP ==========

def enviar_whatsapp(telefone, mensagem):
    """Envia mensagem pelo WhatsApp API da OABRJ"""
    if not telefone:
        print("⚠️ Número de WhatsApp não informado")
        return
    
    try:
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        payload = {
            "session": "oab",
            "sessionkey": "oab",
            "to": telefone,
            "text": mensagem,
        }
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            print(f"✅ Mensagem enviada para {telefone}")
        else:
            print(f"❌ Falha ao enviar mensagem ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp: {e}")


# ========== BUSCA DE ADVOGADOS ==========

def buscar_advogados_no_texto(texto, advogados):
    """Busca advogados no texto do diário"""
    texto_normalizado = normalizar_texto(texto)
    encontrados = []
    
    for advogado in advogados:
        nome_normalizado = normalizar_texto(advogado.nome_completo)
        
        # Busca o nome no texto
        if nome_normalizado in texto_normalizado:
            # Conta quantas vezes o nome aparece
            qtd_mencoes = texto_normalizado.count(nome_normalizado)
            encontrados.append((advogado, qtd_mencoes))
            print(f"✅ {advogado.nome_completo}: {qtd_mencoes} menções")
    
    return encontrados


# ========== SCRAPER PRINCIPAL ==========

def executar_scraper_djerj():
    hoje = datetime.now().date()
    print(f"📅 Verificando DJERJ de {hoje.strftime('%d/%m/%Y')}")

    # Verificar se já processamos hoje
    diario_existente = DiarioOficial.query.filter_by(data_publicacao=hoje).first()
    if diario_existente:
        print("⚠️ DJERJ já processado hoje.")
        return

    # Baixar PDF
    pdf_content = baixar_pdf_durante_sessao(hoje)
    if not pdf_content:
        print("❌ Não foi possível baixar o PDF")
        return

    # Salvar PDF temporariamente
    os.makedirs("temp", exist_ok=True)
    caminho_pdf = f"temp/diario_{hoje.strftime('%Y%m%d')}.pdf"
    with open(caminho_pdf, "wb") as f:
        f.write(pdf_content)

    # Extrair texto
    texto = extrair_texto_pdf(caminho_pdf)
    if len(texto.strip()) < 100:
        print("❌ Texto do PDF muito curto ou inválido")
        os.remove(caminho_pdf)
        return

    # Contar publicações totais (estimativa)
    total_publicacoes = contar_publicacoes_advogados(texto)
    print(f"📊 Total estimado de publicações: {total_publicacoes}")

    # Criar registro do diário
    diario = DiarioOficial(
        data_publicacao=hoje,
        fonte="DJERJ",
        total_publicacoes=total_publicacoes,
        arquivo_pdf=caminho_pdf  # Mantemos o caminho para referência futura
    )
    db.session.add(diario)
    db.session.commit()

    # Buscar advogados cadastrados
    advogados = Advogado.query.all()
    print(f"👨‍💼 Advogados no banco: {len(advogados)}")

    # Procurar advogados no texto
    advogados_encontrados = buscar_advogados_no_texto(texto, advogados)
    
    total_mencoes = 0
    advogados_notificados = 0

    for advogado, qtd_mencoes in advogados_encontrados:
        total_mencoes += qtd_mencoes
        
        # Registrar a publicação
        publicacao = AdvogadoPublicacao(
            advogado_id=advogado.id,
            diario_id=diario.id,
            data_publicacao=hoje,
            qtd_mencoes=qtd_mencoes
        )
        db.session.add(publicacao)

        # Enviar WhatsApp
        mensagem = (
            f"Olá, {advogado.nome_completo}. "
            f"O Recorte Digital da OABRJ encontrou {qtd_mencoes} "
            f"menções em seu nome no Diário da Justiça Eletrônico do Estado do Rio de Janeiro "
            f"({hoje.strftime('%d/%m/%Y')})."
        )
        
        enviar_whatsapp(advogado.whatsapp, mensagem)
        advogados_notificados += 1

    # Atualizar diário com total real de menções
    diario.total_publicacoes = total_mencoes
    db.session.commit()

    print(f"✅ Processamento concluído:")
    print(f"   - Diário: {hoje.strftime('%d/%m/%Y')}")
    print(f"   - Total de menções: {total_mencoes}")
    print(f"   - Advogados encontrados: {len(advogados_encontrados)}")
    print(f"   - Notificações enviadas: {advogados_notificados}")

    # Não removemos o PDF para possível consulta futura
    # os.remove(caminho_pdf)


# ========== MAIN ==========

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper_djerj()
