# app/scrapers/scraper_completo_djerj.py

import requests
from datetime import datetime, date
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

# ========== DOWNLOAD PDF (salva em /tmp) ==========

def baixar_pdf_durante_sessao(data):
    """Baixa o PDF durante a sessão do Selenium e salva em /tmp"""
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

        time.sleep(8)

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for iframe in iframes:
            iframe_src = iframe.get_attribute("src") or ""

            if "pdf.aspx" in iframe_src:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(5)

                    iframe_html = driver.page_source
                    
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
                        if pdf_path.startswith('/consultadje/temp/'):
                            pdf_path = pdf_path.replace('/consultadje/temp/', '')
                        elif pdf_path.startswith('temp/'):
                            pdf_path = pdf_path.replace('temp/', '')
                        
                        pdf_url = f"https://www3.tjrj.jus.br/consultadje/temp/{pdf_path}"
                        print(f"🎯 Tentando URL: {pdf_url}")

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
                                
                                # Salva o PDF no diretório /tmp, que é o correto
                                os.makedirs("/tmp", exist_ok=True)
                                caminho_salvo = f"/tmp/diario_{data.strftime('%Y%m%d')}.pdf"
                                with open(caminho_salvo, "wb") as f:
                                    f.write(response.content)
                                print(f"💾 PDF salvo em: {caminho_salvo}")
                                return caminho_salvo
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

# ========== OUTRAS FUNÇÕES (inalteradas) ==========

def normalizar_texto(texto):
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto

def contar_publicacoes_advogados(texto):
    texto_normalizado = normalizar_texto(texto)
    return texto_normalizado.count('ADVOGADO')

def extrair_texto_pdf(caminho_pdf):
    try:
        texto = extract_text(caminho_pdf)
        print(f"📄 Texto extraído: {len(texto)} caracteres")
        return texto
    except Exception as e:
        print(f"❌ Erro ao extrair texto: {e}")
        return ""

def enviar_whatsapp(telefone, mensagem):
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
    texto_normalizado = normalizar_texto(texto)
    encontrados = []
    
    for advogado in advogados:
        nome_normalizado = normalizar_texto(advogado.nome_completo)
        
        if nome_normalizado in texto_normalizado:
            qtd_mencoes = texto_normalizado.count(nome_normalizado)
            encontrados.append((advogado, qtd_mencoes))
            print(f"✅ {advogado.nome_completo}: {qtd_mencoes} menções")
    
    return encontrados


# ========== FUNÇÃO PRINCIPAL PARA TESTE (Baixa o PDF do dia e testa a notificação) ==========

def executar_scraper_e_testar_notificacao():
    hoje = datetime.now().date()
    print(f"📅 Verificando DJERJ de {hoje.strftime('%d/%m/%Y')}")

    # Este passo é crucial para o teste, pois garante que o arquivo existe
    caminho_pdf = baixar_pdf_durante_sessao(hoje)
    if not caminho_pdf:
        print("❌ Não foi possível baixar o PDF")
        return

    # Extrair texto do PDF recém-baixado
    texto = extrair_texto_pdf(caminho_pdf)
    if len(texto.strip()) < 100:
        print("❌ Texto do PDF muito curto ou inválido")
        os.remove(caminho_pdf)
        return

    # Buscar advogados cadastrados
    advogados = Advogado.query.all()
    print(f"👨‍💼 Advogados no banco: {len(advogados)}")

    # Procurar advogados no texto
    advogados_encontrados = buscar_advogados_no_texto(texto, advogados)
    
    advogados_notificados = 0

    if not advogados_encontrados:
        print("❌ Nenhum advogado encontrado nas publicações de hoje.")
        return

    for advogado, qtd_mencoes in advogados_encontrados:
        mensagem = (
            f"Olá, {advogado.nome_completo}. "
            f"O Recorte Digital da OABRJ encontrou {qtd_mencoes} "
            f"menções em seu nome no Diário da Justiça Eletrônico do Estado do Rio de Janeiro "
            f"({hoje.strftime('%d/%m/%Y')})."
        )
        
        link_diario = f"\nAcesse o Diário completo aqui: https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={hoje.strftime('%d/%m/%Y')}"
        mensagem_final = mensagem + link_diario

        enviar_whatsapp(advogado.whatsapp, mensagem_final)
        advogados_notificados += 1

    # Limpeza do arquivo temporário
    os.remove(caminho_pdf)

    print(f"✅ Teste de notificação concluído:")
    print(f"   - Advogados encontrados: {len(advogados_encontrados)}")
    print(f"   - Notificações enviadas: {advogados_notificados}")


# ========== MAIN ==========

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        # Chame a nova função de teste aqui para uma execução completa e única
        executar_scraper_e_testar_notificacao()
