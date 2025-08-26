# app/scrapers/scraper_completo_djerj.py

import os
import re
import time
import json
import unicodedata
import logging
import requests
from io import StringIO
from datetime import datetime, date
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

from app import db, create_app
from app.models import DiarioOficial, Advogado, AdvogadoPublicacao

# ===================== CONFIGURAÇÃO DE LOGGING =====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===================== CONFIGURAÇÕES =====================
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

def obter_cadernos() -> List[str]:
    """Obtém lista de cadernos a processar from env var."""
    raw = os.getenv("CADERNOS_DJERJ", "E")
    return [c.strip() for c in raw.split(",") if c.strip()]

def caminho_pdf_cache(dt: date, caderno: str) -> str:
    """Retorna caminho do cache para o PDF."""
    d = dt.strftime("%Y%m%d")
    safe_caderno = re.sub(r"[^A-Za-z0-9_-]+", "_", caderno.upper())
    return f"/tmp/diario_{d}_{safe_caderno}.pdf"

# ===================== UTILIDADES DE TEXTO AVANÇADAS =====================
def normalizar_texto(texto: str) -> str:
    """Normalização robusta para busca: acentos, espaços, maiúsculas."""
    if not texto:
        return ""
    
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def criar_regex_oab(numero_oab: str) -> str:
    """Cria regex flexível para todas as variações de OAB."""
    if not numero_oab:
        return ""
    
    oab_clean = re.sub(r'[^\w\s]', ' ', numero_oab.upper())
    oab_clean = re.sub(r'\s+', ' ', oab_clean).strip()
    partes = oab_clean.split()
    
    regex_partes = []
    for parte in partes:
        if parte.isdigit() and len(parte) > 2:
            regex_partes.append(r'[\s\-\.]*' + re.escape(parte) + r'[\s\-\.]*')
        else:
            regex_partes.append(r'[\s\/\-\.]*' + re.escape(parte) + r'[\s\/\-\.]*')
    
    return ''.join(regex_partes)

def criar_regex_nome_flexivel(nome_completo: str) -> str:
    """Cria regex que detecta nomes mesmo quando colados com texto anterior."""
    nome_norm = normalizar_texto(nome_completo)
    partes = nome_norm.split()
    
    regex_partes = []
    for i, parte in enumerate(partes):
        if i == 0:
            regex_partes.append(r'(\w*' + re.escape(parte) + r')')
        else:
            regex_partes.append(r'[\s]?' + re.escape(parte))
    
    return r'\s+'.join(regex_partes)

def buscar_mencoes_advogado(texto_norm: str, advogado: Advogado) -> List[re.Match]:
    """Busca todas as menções válidas do advogado no texto normalizado."""
    resultados = []
    
    nome_pattern = criar_regex_nome_flexivel(advogado.nome_completo)
    
    if advogado.numero_oab:
        oab_pattern = criar_regex_oab(advogado.numero_oab)
        padrao_completo = f"({nome_pattern})" + r".{0,80}?" + f"({oab_pattern})"
        
        for match in re.finditer(padrao_completo, texto_norm, re.IGNORECASE):
            resultados.append(match)
    else:
        for match in re.finditer(nome_pattern, texto_norm, re.IGNORECASE):
            resultados.append(match)
    
    return resultados

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, List[str]]:
    """Extrai texto completo do PDF e retorna texto normalizado + páginas individuais."""
    texto_completo = ""
    paginas_texto = []
    
    with open(pdf_path, "rb") as fp:
        pages = list(PDFPage.get_pages(fp))
        
        for page in pages:
            resource_manager = PDFResourceManager()
            buf = StringIO()
            converter = TextConverter(resource_manager, buf, laparams=LAParams())
            interpreter = PDFPageInterpreter(resource_manager, converter)
            
            try:
                interpreter.process_page(page)
                texto_pagina = buf.getvalue()
                paginas_texto.append(texto_pagina)
                texto_completo += texto_pagina + "\n"
            finally:
                converter.close()
                buf.close()
    
    return normalizar_texto(texto_completo), paginas_texto

# ===================== WHATSAPP OTIMIZADO =====================
def enviar_whatsapp(telefone: str, mensagem: str) -> bool:
    """Envia mensagem via API da UZAPI com retorno de sucesso."""
    if not telefone:
        logger.warning("Número de WhatsApp não informado")
        return False

    try:
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        headers = {"Content-Type": "application/json", "sessionkey": "oab"}
        payload = {"session": "oab", "number": telefone, "text": mensagem}

        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"Mensagem enviada para {telefone}")
            return True
        else:
            logger.error(f"Erro WhatsApp ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erro WhatsApp: {e}")
        return False
    finally:
        time.sleep(2.0)

# ===================== DOWNLOAD / CACHE OTIMIZADO =====================
def baixar_pdf_durante_sessao(dt: date, caderno: str) -> str | None:
    """Baixa o PDF durante a sessão do Selenium com melhor tratamento de erro."""
    destino = caminho_pdf_cache(dt, caderno)
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        logger.info(f"Cache encontrado para {dt.strftime('%d/%m/%Y')} [{caderno}]: {destino}")
        return destino

    logger.info(f"Buscando PDF para {dt.strftime('%d/%m/%Y')} [caderno={caderno}]...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-agent={USER_AGENT}")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        url = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina=-1"
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

            logger.info(f"URLs candidatas ({len(candidates)}): {list(candidates)[:3]}{'...' if len(candidates)>3 else ''}")

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
                logger.info(f"Tentando URL: {pdf_url}")

                try:
                    response = session.get(pdf_url, headers=headers, timeout=30)
                    logger.info(f"Status: {response.status_code}, bytes: {len(response.content)}")
                    
                    if response.status_code == 200 and response.content.startswith(b"%PDF"):
                        os.makedirs("/tmp", exist_ok=True)
                        with open(destino, "wb") as f:
                            f.write(response.content)
                        logger.info(f"PDF salvo em: {destino}")
                        return destino
                        
                except Exception as e:
                    logger.warning(f"Falha ao baixar candidato: {e}")

            driver.switch_to.default_content()

        logger.error("Nenhum PDF válido encontrado")
        return None
        
    except Exception as e:
        logger.error(f"Erro durante download: {e}")
        return None
    finally:
        driver.quit()

# ===================== PROCESSAMENTO OTIMIZADO =====================
def processar_pdf_otimizado(dt: date, caderno: str, caminho_pdf: str) -> Tuple[int, Dict[int, List[Dict]]]:
    """Processamento otimizado: extrai texto uma vez e busca todos os advogados."""
    total_mencoes = 0
    por_advogado = defaultdict(list)

    # Carrega todos os advogados
    advogados = Advogado.query.all()
    logger.info(f"{len(advogados)} advogados cadastrados. Buscando menções...")

    # Extrai texto completo de uma vez (mais eficiente)
    texto_norm_completo, paginas_texto = extract_text_from_pdf(caminho_pdf)
    logger.info(f"Processando {len(paginas_texto)} páginas do caderno {caderno}...")

    # Pré-processa padrões OAB para busca rápida
    padroes_oab = []
    for advogado in advogados:
        if advogado.numero_oab:
            oab_pattern = criar_regex_oab(advogado.numero_oab)
            padroes_oab.append((advogado, oab_pattern))

    # Busca por ocorrências de OAB primeiro (mais específico)
    ocorrencias_potenciais = []
    for advogado, oab_pattern in padroes_oab:
        for match in re.finditer(oab_pattern, texto_norm_completo, re.IGNORECASE):
            ocorrencias_potenciais.append((match.start(), match.end(), advogado))

    # Para cada ocorrência potencial, verifica se o nome está próximo
    for start, end, advogado in ocorrencias_potenciais:
        # Verifica contexto around da OAB
        ctx_ini = max(0, start - 100)
        ctx_fim = min(len(texto_norm_completo), end + 100)
        contexto = texto_norm_completo[ctx_ini:ctx_fim]
        
        nome_pattern = criar_regex_nome_flexivel(advogado.nome_completo)
        if re.search(nome_pattern, contexto, re.IGNORECASE):
            # Encontrou correspondência! Descobre a página
            pagina = 1
            acumulado = 0
            for i, texto_pagina in enumerate(paginas_texto, 1):
                acumulado += len(texto_pagina)
                if start <= acumulado:
                    pagina = i
                    break

            total_mencoes += 1
            contexto_completo = texto_norm_completo[max(0, start-120):min(len(texto_norm_completo), end+120)].strip()
            
            mencao = {
                "advogado": advogado,
                "pagina": pagina,
                "contexto": contexto_completo,
                "link": f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina={pagina}",
                "data_publicacao": dt,
                "caderno": caderno,
            }

            por_advogado[advogado.id].append(mencao)
            logger.info(f"Menção confirmada: {advogado.nome_completo} - Página {pagina}")

    # Busca fallback para advogados sem OAB
    for advogado in advogados:
        if not advogado.numero_oab:
            matches = buscar_mencoes_advogado(texto_norm_completo, advogado)
            for match in matches:
                total_mencoes += 1
                start, end = match.span()
                
                # Descobre a página
                pagina = 1
                acumulado = 0
                for i, texto_pagina in enumerate(paginas_texto, 1):
                    acumulado += len(texto_pagina)
                    if start <= acumulado:
                        pagina = i
                        break

                contexto = texto_norm_completo[max(0, start-120):min(len(texto_norm_completo), end+120)].strip()
                
                mencao = {
                    "advogado": advogado,
                    "pagina": pagina,
                    "contexto": contexto,
                    "link": f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina={pagina}",
                    "data_publicacao": dt,
                    "caderno": caderno,
                }

                por_advogado[advogado.id].append(mencao)
                logger.info(f"Menção fallback: {advogado.nome_completo} - Página {pagina}")

    return total_mencoes, dict(por_advogado)

def _filter_kwargs(model_cls, **kwargs):
    """Mantém apenas colunas que existem no model."""
    cols = set(c.name for c in model_cls.__table__.columns)
    return {k: v for k, v in kwargs.items() if k in cols}

def persistir_resultados(dt: date, caderno: str, caminho_pdf: str, total_mencoes: int, por_advogado: dict):
    """Persiste resultados no banco de dados."""
    q = DiarioOficial.query.filter_by(data_publicacao=dt)
    if "caderno" in (c.name for c in DiarioOficial.__table__.columns):
        q = q.filter_by(caderno=caderno)
    if q.first():
        logger.warning(f"Diário já existente para {dt.strftime('%d/%m/%Y')} [{caderno}]. Pulando persistência.")
        return q.first()

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
        logger.info(f"Diário persistido: {dt.strftime('%d/%m/%Y')} [{caderno}] – {total_mencoes} menções")
        return diario

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao persistir resultados: {e}")
        raise

# ===================== NOTIFICAÇÕES AGRUPADAS =====================
def enviar_notificacoes_agrupadas(por_advogado: dict, dt: date, caderno: str) -> int:
    """Envia uma única mensagem agrupada por advogado."""
    total_msgs = 0
    
    for adv_id, mencoes in por_advogado.items():
        if not mencoes:
            continue
            
        advogado = mencoes[0]["advogado"]
        
        if not getattr(advogado, "whatsapp", None):
            logger.warning(f"{advogado.nome_completo} sem WhatsApp cadastrado. Pulando.")
            continue

        # Prepara mensagem agrupada
        paginas = sorted(set(m["pagina"] for m in mencoes))
        mensagem = (
            f"*Recorte Digital - OABRJ* 📋\n\n"
            f"*Olá, {advogado.nome_completo}!* 👋\n\n"
            f"Encontramos *{len(mencoes)} menções* no DJERJ de {dt.strftime('%d/%m/%Y')}:\n"
            f"• Caderno: {caderno}\n"
            f"• Páginas: {', '.join(map(str, paginas))}\n\n"
        )

        # Adiciona exemplos de trechos (máximo 3)
        for i, mencao in enumerate(mencoes[:3], 1):
            mensagem += f"*📖 Exemplo {i} (Página {mencao['pagina']}):*\n"
            mensagem += f'"{mencao["contexto"][:200]}{"..." if len(mencao["contexto"]) > 200 else ""}"\n\n'

        mensagem += (
            f"*🔗 Links diretos:*\n"
        )
        
        # Adiciona links únicos por página
        paginas_links = {}
        for mencao in mencoes:
            if mencao["pagina"] not in paginas_links:
                paginas_links[mencao["pagina"]] = mencao["link"]
        
        for pagina, link in paginas_links.items():
            mensagem += f"• Página {pagina}: {link}\n"

        mensagem += "\n*💼 Dúvidas?* Entre em contato com a OABRJ."

        # Envia mensagem agrupada
        if enviar_whatsapp(advogado.whatsapp, mensagem):
            total_msgs += 1

        time.sleep(1.0)

    logger.info(f"Notificações agrupadas enviadas: {total_msgs}")
    return total_msgs

# ===================== ORQUESTRAÇÃO PRINCIPAL =====================
def executar_scraper_completo():
    """Função principal de orquestração do scraper."""
    dt = datetime.now().date()
    inicio = time.time()
    logger.info(f"Processando DJERJ de {dt.strftime('%d/%m/%Y')}")
    logger.info(f"Início: {datetime.now().strftime('%H:%M:%S')}")

    cadernos = obter_cadernos()
    logger.info(f"Cadernos configurados: {', '.join(cadernos)}")

    total_geral_mencoes = 0
    total_geral_msgs = 0

    for caderno in cadernos:
        logger.info(f"\n===== CADERNO: {caderno} =====")

        # Verifica se já foi processado
        q = DiarioOficial.query.filter_by(data_publicacao=dt)
        if "caderno" in (c.name for c in DiarioOficial.__table__.columns):
            q = q.filter_by(caderno=caderno)
        if q.first():
            logger.warning(f"Diário já processado para {dt.strftime('%d/%m/%Y')} [{caderno}]. Pulando.")
            continue

        # Download do PDF
        caminho = baixar_pdf_durante_sessao(dt, caderno)
        if not caminho:
            logger.error(f"Falha ao obter PDF para caderno {caderno}")
            continue

        # Processamento otimizado
        total_mencoes, por_advogado = processar_pdf_otimizado(dt, caderno, caminho)
        total_geral_mencoes += total_mencoes

        # Persistência e notificações
        diario = persistir_resultados(dt, caderno, caminho, total_mencoes, por_advogado)
        msgs_enviadas = enviar_notificacoes_agrupadas(por_advogado, dt, caderno)
        total_geral_msgs += msgs_enviadas

    # Relatório final
    dur = time.time() - inicio
    logger.info("\n" + "="*50)
    logger.info(f"✅ Processamento concluído em {dur:.2f} segundos")
    logger.info(f"📊 Menções totais encontradas: {total_geral_mencoes}")
    logger.info(f"✉️ Notificações enviadas: {total_geral_msgs}")
    logger.info(f"⏰ Fim: {datetime.now().strftime('%H:%M:%S')}")

# ===================== MAIN =====================
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper_completo()
