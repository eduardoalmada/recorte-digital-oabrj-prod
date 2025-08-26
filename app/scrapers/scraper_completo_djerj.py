import requests
import time
import os
import re
import unicodedata
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO

from app import db, create_app
from app.models import DiarioOficial, Advogado, AdvogadoPublicacao


# ========== FUNÇÕES UTILITÁRIAS ==========

def normalizar_texto(texto: str) -> str:
    """Remove acentos e converte para maiúsculas para busca mais confiável."""
    texto = texto.upper()
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')


def enviar_whatsapp(telefone: str, mensagem: str):
    """Envia mensagem via API da UZAPI."""
    if not telefone:
        print("⚠️ Número de WhatsApp não informado")
        return
    
    try:
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        headers = {"Content-Type": "application/json", "sessionkey": "oab"}
        payload = {"session": "oab", "number": telefone, "text": mensagem}
        
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            print(f"✅ Mensagem enviada para {telefone}")
        else:
            print(f"❌ Erro ({r.status_code}): {r.text}")
        time.sleep(3)  # Rate limiting aumentado para segurança
    except Exception as e:
        print(f"❌ Erro WhatsApp: {e}")
        time.sleep(5)


def extract_text_from_page(page):
    """Extrai texto de uma única página PDF de forma eficiente."""
    resource_manager = PDFResourceManager()
    fake_file_handle = StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    interpreter = PDFPageInterpreter(resource_manager, converter)
    
    interpreter.process_page(page)
    text = fake_file_handle.getvalue()
    
    converter.close()
    fake_file_handle.close()
    
    return text


# ========== DOWNLOAD PDF ==========

def baixar_pdf_durante_sessao(data):
    """Baixa o PDF durante a sessão do Selenium e salva em /tmp."""
    print(f'🔍 Buscando PDF para {data.strftime("%d/%m/%Y")}...')

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        url = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={data.strftime('%d/%m/%Y')}&caderno=E&pagina=-1"
        driver.get(url)
        time.sleep(6)

        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            iframe_src = iframe.get_attribute("src") or ""
            if "pdf.aspx" in iframe_src:
                driver.switch_to.frame(iframe)
                time.sleep(4)

                iframe_html = driver.page_source
                pdf_urls = re.findall(r"(temp/[^\"']+\.pdf)", iframe_html, re.IGNORECASE)

                for pdf_path in pdf_urls:
                    pdf_url = f"https://www3.tjrj.jus.br/consultadje/{pdf_path.lstrip('/')}"
                    print(f"🎯 Tentando URL: {pdf_url}")

                    cookies = driver.get_cookies()
                    session = requests.Session()
                    for cookie in cookies:
                        session.cookies.set(cookie["name"], cookie["value"])

                    response = session.get(pdf_url, timeout=30)
                    if response.status_code == 200 and response.content.startswith(b"%PDF"):
                        os.makedirs("/tmp", exist_ok=True)
                        caminho_pdf = f"/tmp/diario_{data.strftime('%Y%m%d')}.pdf"
                        with open(caminho_pdf, "wb") as f:
                            f.write(response.content)
                        print(f"💾 PDF salvo em {caminho_pdf}")
                        return caminho_pdf
        return None
    finally:
        driver.quit()


# ========== FUNÇÃO PRINCIPAL ==========

def executar_scraper_completo():
    hoje = datetime.now().date()
    start_time = time.time()
    print(f"📅 Processando DJERJ de {hoje.strftime('%d/%m/%Y')}")
    print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")

    # Verificar se diário já foi processado
    diario_existente = DiarioOficial.query.filter_by(data_publicacao=hoje).first()
    if diario_existente:
        print("⚠️ Diário já processado.")
        return

    # Baixar PDF
    caminho_pdf = baixar_pdf_durante_sessao(hoje)
    if not caminho_pdf:
        print("❌ Falha no download do PDF")
        return

    total_mencoes = 0
    advogados_encontrados_por_diario = {}

    try:
        # Iniciar transação explicitamente para garantir atomicidade
        db.session.begin()
        
        # Carregar todos os advogados uma única vez
        advogados = Advogado.query.all()
        print(f"👨‍💼 {len(advogados)} advogados cadastrados. Buscando menções...")
        
        # Criar dicionário para acesso rápido
        advogados_dict = {normalizar_texto(a.nome_completo): a for a in advogados}

        with open(caminho_pdf, "rb") as f:
            pages = list(PDFPage.get_pages(f))
            total_pages = len(pages)
            print(f"📄 Processando {total_pages} páginas...")
            
            # Registrar o Diário e vincular as publicações em uma única transação
            diario = DiarioOficial(
                data_publicacao=hoje,
                fonte="DJERJ",
                total_publicacoes=0, # Inicia com 0, será atualizado ao final
                arquivo_pdf=caminho_pdf
            )
            db.session.add(diario)

            for page_num, page in enumerate(pages, 1):
                try:
                    page_text = extract_text_from_page(page)
                    if not page_text or len(page_text.strip()) < 50:
                        continue

                    texto_norm_pagina = normalizar_texto(page_text)
                    
                    for nome_normalizado, advogado in advogados_dict.items():
                        if nome_normalizado in texto_norm_pagina:
                            
                            ocorrencias = [m.start() for m in re.finditer(re.escape(nome_normalizado), texto_norm_pagina)]
                            
                            for posicao in ocorrencias:
                                total_mencoes += 1
                                inicio_ctx = max(0, posicao - 100)
                                fim_ctx = min(len(texto_norm_pagina), posicao + len(nome_normalizado) + 100)
                                contexto = texto_norm_pagina[inicio_ctx:fim_ctx].strip()
                                link_publicacao = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={hoje.strftime('%d/%m/%Y')}&caderno=E&pagina={page_num}"
                                
                                publicacao = AdvogadoPublicacao(
                                    advogado_id=advogado.id,
                                    diario_id=diario.id, # Vincula diretamente ao objeto de diário
                                    data_publicacao=hoje,
                                    pagina=page_num,
                                    contexto=contexto,
                                    titulo=f"Publicação DJERJ - {advogado.nome_completo} - Página {page_num}",
                                    tribunal="Tribunal de Justiça do Estado do Rio de Janeiro",
                                    jornal="Diário da Justiça Eletrônico do Estado do Rio de Janeiro",
                                    caderno="E",
                                    local="Rio de Janeiro",
                                    mensagem=f"Menção encontrada na página {page_num} do DJERJ",
                                    link=link_publicacao,
                                    qtd_mencoes=1
                                )
                                db.session.add(publicacao)

                                if advogado.id not in advogados_encontrados_por_diario:
                                     advogados_encontrados_por_diario[advogado.id] = {
                                         'obj': advogado,
                                         'mencoes': []
                                     }
                                advogados_encontrados_por_diario[advogado.id]['mencoes'].append(publicacao)
                                print(f"📍 Menção de {advogado.nome_completo} encontrada na página {page_num}")
                
                except Exception as e:
                    print(f"⚠️ Erro ao processar página {page_num}: {e}")
                    continue
        
        # Atualiza o total de publicações do diário
        diario.total_publicacoes = total_mencoes
        
        # Faz o commit único para todo o processo
        db.session.commit()
        
        # Enviar notificações
        notificacoes_enviadas = 0
        for advogado_id, data in advogados_encontrados_por_diario.items():
            advogado = data['obj']
            mencoes = data['mencoes']
            
            if not advogado.whatsapp:
                print(f"⚠️ Advogado {advogado.nome_completo} sem WhatsApp cadastrado")
                continue
            
            mensagens = []
            for i, mencao in enumerate(mencoes, 1):
                mensagem_bloco = f"""*Publicação {i} de {len(mencoes)}* no DJERJ de {hoje.strftime('%d/%m/%Y')}.

*📄 Página:* {mencao.pagina}

*📖 Trecho encontrado:*
"{mencao.contexto}"

*🔗 Link direto:* {mencao.link}"""
                mensagens.append(mensagem_bloco)

            mensagem_final = f"""*📋 Recorte Digital - OABRJ* 🎯

*Olá, {advogado.nome_completo}.*

Foram encontradas {len(mencoes)} publicações em seu nome.
------------------------------------
{"\n\n".join(mensagens)}

*💼 Dúvidas?* Entre em contato com a OABRJ.

*OABRJ - Recorte Digital* 📊
*Monitoramento inteligente de publicações*"""

            
            enviar_whatsapp(advogado.whatsapp, mensagem_final)
            notificacoes_enviadas += 1
            time.sleep(1)  # Pausa entre notificações

        elapsed_time = time.time() - start_time
        print(f"✅ Processamento concluído em {elapsed_time:.2f} segundos")
        print(f"📊 Estatísticas: {total_mencoes} menções, {notificacoes_enviadas} notificações enviadas")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro fatal: {e}")
        raise
    finally:
        if 'caminho_pdf' in locals() and os.path.exists(caminho_pdf):
            os.remove(caminho_pdf)
            print(f"🧹 PDF temporário removido: {caminho_pdf}")
        
        print(f"⏰ Fim: {datetime.now().strftime('%H:%M:%S')}")


# ========== MAIN ==========

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper_completo()
