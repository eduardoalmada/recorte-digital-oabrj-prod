# app/scrapers/scraper_completo_djerj.py

import os
import re
import time
import json
import unicodedata
import requests
from io import StringIO
from datetime import datetime, date
from typing import List, Pattern, Match

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

from app import db, create_app
from app.models import DiarioOficial, Advogado, AdvogadoPublicacao


# ===================== CONFIG =====================

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Cadernos a processar. Defina na env var CADERNOS_DJERJ="E,ADMINISTRATIVO,JUDICIARIO"
def obter_cadernos():
    raw = os.getenv("CADERNOS_DJERJ", "E")
    return [c.strip() for c in raw.split(",") if c.strip()]

# Caminho do cache (/tmp) para um PDF específico
def caminho_pdf_cache(dt: date, caderno: str) -> str:
    d = dt.strftime("%Y%m%d")
    safe_caderno = re.sub(r"[^A-Za-z0-9_-]+", "_", caderno.upper())
    return f"/tmp/diario_{d}_{safe_caderno}.pdf"


# ===================== UTILIDADES DE TEXTO =====================

def normalizar_texto(texto: str) -> str:
    """Normalização robusta: acentos, espaços, maiúsculas e limpeza."""
    if not texto:
        return ""
    
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'\s+', ' ', texto)  # Normaliza múltiplos espaços
    return texto.strip()

def criar_regex_oab(numero_oab: str) -> str:
    """Cria regex flexível para todas as variações de OAB."""
    if not numero_oab:
        return ""
    
    # Limpa e normaliza a OAB
    oab_clean = re.sub(r'[^\w\s]', ' ', numero_oab.upper())
    oab_clean = re.sub(r'\s+', ' ', oab_clean).strip()
    partes = oab_clean.split()
    
    regex_partes = []
    for parte in partes:
        if parte.isdigit() and len(parte) > 2:
            # Parte numérica: permite 211, 211., 211-, 211 
            regex_partes.append(r'[\s\-\.]*' + re.escape(parte) + r'[\s\-\.]*')
        else:
            # Texto: permite OAB, OAB/, OAB-, OAB 
            regex_partes.append(r'[\s\/\-\.]*' + re.escape(parte) + r'[\s\/\-\.]*')
    
    return ''.join(regex_partes)

def criar_regex_nome_flexivel(nome_completo: str) -> str:
    """Cria regex que detecta nomes mesmo quando colados com texto anterior."""
    nome_norm = normalizar_texto(nome_completo)
    partes = nome_norm.split()
    
    regex_partes = []
    for i, parte in enumerate(partes):
        if i == 0:
            # Primeira parte: pode estar colada com texto antes
            regex_partes.append(r'(\w*' + re.escape(parte) + r')')
        else:
            # Partes seguintes: devem ter espaço ou estar coladas
            regex_partes.append(r'[\s]?' + re.escape(parte))
    
    return r'\s+'.join(regex_partes)

def buscar_mencoes_advogado(texto_norm: str, advogado: Advogado) -> List[Match]:
    """Busca todas as menções válidas do advogado no texto normalizado."""
    resultados = []
    
    # Padrão flexível para nome (com detecção de nomes colados)
    nome_pattern = criar_regex_nome_flexivel(advogado.nome_completo)
    
    if advogado.numero_oab:
        # Padrão super flexível para OAB
        oab_pattern = criar_regex_oab(advogado.numero_oab)
        
        # Padrão combinado: nome + OAB com proximidade (até 80 caracteres)
        padrao_completo = f"({nome_pattern})" + r".{0,80}?" + f"({oab_pattern})"
        
        # Busca todas as ocorrências
        for match in re.finditer(padrao_completo, texto_norm, re.IGNORECASE):
            resultados.append(match)
    else:
        # Fallback: busca apenas pelo nome
        for match in re.finditer(nome_pattern, texto_norm, re.IGNORECASE):
            resultados.append(match)
    
    return resultados

def extract_text_from_page(page) -> str:
    """Extrai texto de uma única página PDF de forma eficiente."""
    resource_manager = PDFResourceManager()
    buf = StringIO()
    converter = TextConverter(resource_manager, buf, laparams=LAParams())
    interpreter = PDFPageInterpreter(resource_manager, converter)
    try:
        interpreter.process_page(page)
        return buf.getvalue()
    finally:
        converter.close()
        buf.close()

def _filter_kwargs(model_cls, **kwargs):
    """Mantém apenas colunas que existem no model para evitar TypeError."""
    cols = set(c.name for c in model_cls.__table__.columns)
    return {k: v for k, v in kwargs.items() if k in cols}


# ===================== WHATSAPP =====================

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
            print(f"❌ Erro WhatsApp ({r.status_code}): {r.text}")
        time.sleep(2.0)
    except Exception as e:
        print(f"❌ Erro WhatsApp: {e}")
        time.sleep(4.0)


# ===================== DOWNLOAD / CACHE =====================

def baixar_pdf_durante_sessao(dt: date, caderno: str) -> str | None:
    """Baixa o PDF durante a sessão do Selenium e salva em /tmp."""
    destino = caminho_pdf_cache(dt, caderno)
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        print(f"🟢 Cache encontrado para {dt.strftime('%d/%m/%Y')} [{caderno}]: {destino}")
        return destino

    print(f"🔍 Buscando PDF para {dt.strftime('%d/%m/%Y')} [caderno={caderno}]...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-agent={USER_AGENT}")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        url = (
            "https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx"
            f"?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina=-1"
        )
        driver.get(url)
        time.sleep(6)

        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src") or ""
            if "pdf.aspx" not in src:
                continue

            driver.switch_to.frame(iframe)
            time.sleep(3)

            html = driver.page_source or ""
            candidates = set()
            for pat in (
                r"(?:['\"])((?:/)?temp/[^\"']+?\.pdf)(?:['\"])",
                r"(?:filename=)([^&\"']+?\.pdf)",
                r"openPDF\('([^']+?\.pdf)'\)",
            ):
                for m in re.findall(pat, html, flags=re.IGNORECASE):
                    candidates.add(m.strip())

            if not candidates:
                driver.switch_to.default_content()
                continue

            print(f"📝 URLs candidatas ({len(candidates)}): {list(candidates)[:3]}{'...' if len(candidates)>3 else ''}")

            cookies = driver.get_cookies()
            session = requests.Session()
            for c in cookies:
                try:
                    session.cookies.set(c["name"], c["value"])
                except Exception:
                    pass

            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/pdf, */*",
                "Referer": driver.current_url,
            }

            for path in candidates:
                clean_path = path.lstrip("/").replace("consultadje/", "").strip()
                if not clean_path.lower().startswith("temp/"):
                    clean_path = f"temp/{clean_path}"

                pdf_url = f"https://www3.tjrj.jus.br/consultadje/{clean_path}"
                print(f"🎯 Tentando URL: {pdf_url}")

                try:
                    r = session.get(pdf_url, headers=headers, timeout=30)
                    print(f"📊 Status: {r.status_code}, bytes: {len(r.content)}")
                    if r.status_code == 200 and r.content.startswith(b"%PDF"):
                        os.makedirs("/tmp", exist_ok=True)
                        with open(destino, "wb") as f:
                            f.write(r.content)
                        print(f"💾 PDF salvo em: {destino}")
                        return destino
                except Exception as e:
                    print(f"⚠️ Falha ao baixar candidato: {e}")

            driver.switch_to.default_content()

        print("❌ Nenhum PDF válido encontrado")
        return None
    finally:
        driver.quit()


# ===================== PROCESSAMENTO =====================

def processar_pdf(dt: date, caderno: str, caminho_pdf: str):
    """Varre o PDF por página, encontra menções e retorna resultados."""
    total_mencoes = 0
    por_advogado = {}

    # Carrega todos os advogados
    advogados = Advogado.query.all()
    print(f"👨‍💼 {len(advogados)} advogados cadastrados. Buscando menções...")

    with open(caminho_pdf, "rb") as fp:
        pages = list(PDFPage.get_pages(fp))
        print(f"📄 Processando {len(pages)} páginas do caderno {caderno}...")

        for page_num, page in enumerate(pages, 1):
            try:
                raw_text = extract_text_from_page(page)
                if not raw_text or len(raw_text.strip()) < 50:
                    continue

                texto_norm = normalizar_texto(raw_text)

                # Processa CADA advogado individualmente para busca precisa
                for advogado in advogados:
                    matches = buscar_mencoes_advogado(texto_norm, advogado)
                    
                    for match in matches:
                        total_mencoes += 1
                        start, end = match.span()
                        
                        # Contexto para mostrar no WhatsApp
                        ctx_ini = max(0, start - 120)
                        ctx_fim = min(len(texto_norm), end + 120)
                        contexto = texto_norm[ctx_ini:ctx_fim].strip()

                        link_publicacao = (
                            "https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx"
                            f"?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina={page_num}"
                        )

                        mencao = {
                            "advogado": advogado,
                            "pagina": page_num,
                            "contexto": contexto,
                            "link": link_publicacao,
                            "data_publicacao": dt,
                            "caderno": caderno,
                        }

                        por_advogado.setdefault(advogado.id, []).append(mencao)
                        print(f"📍 Menção confirmada: {advogado.nome_completo} - Página {page_num}")

                if page_num % 20 == 0:
                    print(f"    • {page_num} páginas varridas...")

            except Exception as e:
                print(f"⚠️ Erro ao processar página {page_num}: {e}")
                continue

    return total_mencoes, por_advogado

def persistir_resultados(dt: date, caderno: str, caminho_pdf: str, total_mencoes: int, por_advogado: dict):
    """Cria o registro do Diário e todas as publicações numa transação."""
    q = DiarioOficial.query.filter_by(data_publicacao=dt)
    if "caderno" in (c.name for c in DiarioOficial.__table__.columns):
        q = q.filter_by(caderno=caderno)
    existente = q.first()
    if existente:
        print(f"⚠️ Diário já existente para {dt.strftime('%d/%m/%Y')} [{caderno}]. Pulando persistência.")
        return existente

    try:
        diario_kwargs = _filter_kwargs(
            DiarioOficial,
            data_publicacao=dt,
            fonte="DJERJ",
            caderno=caderno,
            total_publicacoes=total_mencoes,
            arquivo_pdf=caminho_pdf,
        )
        diario = DiarioOficial(**diario_kwargs)
        db.session.add(diario)
        db.session.flush()

        for adv_id, mencoes in por_advogado.items():
            for m in mencoes:
                pub_kwargs = _filter_kwargs(
                    AdvogadoPublicacao,
                    advogado_id=m["advogado"].id,
                    diario_id=diario.id,
                    data_publicacao=dt,
                    pagina=m["pagina"],
                    contexto=m["contexto"],
                    titulo=f"Publicação DJERJ - {m['advogado'].nome_completo} - Página {m['pagina']}",
                    tribunal="Tribunal de Justiça do Estado do Rio de Janeiro",
                    jornal="Diário da Justiça Eletrônico do Estado do Rio de Janeiro",
                    caderno=caderno,
                    local="Rio de Janeiro",
                    mensagem=f"Menção encontrada na página {m['pagina']} do DJERJ",
                    link=m["link"],
                    qtd_mencoes=1,
                )
                db.session.add(AdvogadoPublicacao(**pub_kwargs))

        db.session.commit()
        print(f"💽 Diário persistido: {dt.strftime('%d/%m/%Y')} [{caderno}] – {total_mencoes} menções")
        return diario

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao persistir resultados: {e}")
        raise

def enviar_notificacoes(por_advogado: dict, dt: date, caderno: str):
    """Envia UMA mensagem por menção (link direto da página)."""
    total_msgs = 0
    for adv_id, mencoes in por_advogado.items():
        advogado = mencoes[0]["advogado"] if mencoes else None
        if not advogado:
            continue

        if not getattr(advogado, "whatsapp", None):
            print(f"⚠️ {advogado.nome_completo} sem WhatsApp cadastrado. Pulando.")
            continue

        for idx, m in enumerate(mencoes, 1):
            mensagem = (
                f"*Recorte Digital - OABRJ*\n"
                f"📅 {dt.strftime('%d/%m/%Y')} • Caderno: {caderno} • Página: {m['pagina']}\n\n"
                f"🔎 Trecho:\n{m['contexto']}\n\n"
                f"🔗 Link direto: {m['link']}"
            )
            enviar_whatsapp(advogado.whatsapp, mensagem)
            total_msgs += 1

        time.sleep(1.0)

    print(f"📨 Notificações enviadas: {total_msgs}")


# ===================== ORQUESTRAÇÃO =====================

def executar_scraper_completo():
    dt = datetime.now().date()
    inicio = time.time()
    print(f"📅 Processando DJERJ de {dt.strftime('%d/%m/%Y')}")
    print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")

    cadernos = obter_cadernos()
    print(f"🗂️ Cadernos configurados: {', '.join(cadernos)}")

    total_geral_mencoes = 0
    total_geral_msgs = 0

    for caderno in cadernos:
        print(f"\n===== CADERNO: {caderno} =====")

        q = DiarioOficial.query.filter_by(data_publicacao=dt)
        if "caderno" in (c.name for c in DiarioOficial.__table__.columns):
            q = q.filter_by(caderno=caderno)
        if q.first():
            print(f"⚠️ Diário já processado para {dt.strftime('%d/%m/%Y')} [{caderno}]. Pulando.")
            continue

        caminho = baixar_pdf_durante_sessao(dt, caderno)
        if not caminho:
            print(f"❌ Falha ao obter PDF para caderno {caderno}")
            continue

        total_mencoes, por_advogado = processar_pdf(dt, caderno, caminho)
        total_geral_mencoes += total_mencoes

        diario = persistir_resultados(dt, caderno, caminho, total_mencoes, por_advogado)
        enviar_notificacoes(por_advogado, dt, caderno)
        total_geral_msgs += sum(len(v) for v in por_advogado.values())

    dur = time.time() - inicio
    print("\n==============================")
    print(f"✅ Concluído em {dur:.2f}s")
    print(f"📊 Menções totais: {total_geral_mencoes}")
    print(f"✉️ Mensagens enviadas: {total_geral_msgs}")
    print(f"⏰ Fim: {datetime.now().strftime('%H:%M:%S')}")


# ===================== MAIN =====================

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper_completo()
