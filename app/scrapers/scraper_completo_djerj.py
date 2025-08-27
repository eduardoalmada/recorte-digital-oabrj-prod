# app/scrapers/scraper_completo_djerj.py (Versão Final Otimizada)

import os
import re
import time
import json
import unicodedata
import logging
import requests
from io import StringIO
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Set, Tuple, Match
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

from app import db, create_app
from app.models import DiarioOficial, Advogado, AdvogadoPublicacao

# ===================== TIMEZONE =====================
TZ_SP = ZoneInfo("America/Sao_Paulo")

# ===================== CONFIGURAÇÃO DE LOGGING =====================
class TZFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, tz: ZoneInfo | None = None):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tz = tz or ZoneInfo("UTC")

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

root_logger = logging.getLogger()
root_logger.handlers = []
handler = logging.StreamHandler()
handler.setFormatter(TZFormatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S', tz=TZ_SP))
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)
logger = logging.getLogger(__name__)

# ===================== CONFIGURAÇÕES =====================
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
MAX_RETRIES = 3
WHATSAPP_THREADS = int(os.getenv("WHATSAPP_THREADS", "8"))
advogado_patterns = {}  # Cache para regex pré-compilada

def obter_cadernos() -> List[str]:
    raw = os.getenv("CADERNOS_DJERJ", "E")
    return [c.strip() for c in raw.split(",") if c.strip()]

def caminho_pdf_cache(dt: date, caderno: str) -> str:
    cache_dir = os.getenv("CACHE_DIR", "/tmp")
    os.makedirs(cache_dir, exist_ok=True)
    d = dt.strftime("%Y%m%d")
    safe_caderno = re.sub(r"[^A-Za-z0-9_-]+", "_", caderno.upper())
    return f"{cache_dir}/diario_{d}_{safe_caderno}.pdf"

# ===================== UTILIDADES DE TEXTO AVANÇADAS =====================
def normalizar_texto(texto: str) -> str:
    if not texto: return ""
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

OAB_PATTERN = re.compile(r'[\s\-\/\.]*')
def criar_regex_oab(numero_oab: str) -> re.Pattern:
    if not numero_oab: return re.compile("")
    oab_clean = normalizar_texto(numero_oab)
    partes = oab_clean.split()
    regex_partes = [re.escape(parte) for parte in partes]
    return re.compile(OAB_PATTERN.pattern.join(regex_partes))

NOME_PATTERN = re.compile(r'[\s]?')
def criar_regex_nome_flexivel(nome_completo: str) -> re.Pattern:
    nome_norm = normalizar_texto(nome_completo)
    partes = nome_norm.split()
    regex_partes = []
    for i, parte in enumerate(partes):
        if i == 0: regex_partes.append(r'(\w*' + re.escape(parte) + r')')
        else: regex_partes.append(re.escape(parte))
    return re.compile(r'\s+'.join(regex_partes))

def buscar_mencoes_advogado(texto_norm: str, advogado: Advogado) -> List[Match]:
    resultados = []
    if advogado.id not in advogado_patterns:
        advogado_patterns[advogado.id] = {
            'nome': criar_regex_nome_flexivel(advogado.nome_completo),
            'oab': criar_regex_oab(advogado.numero_oab) if advogado.numero_oab else None
        }
    
    patterns = advogado_patterns[advogado.id]
    if patterns['oab']:
        padrao_completo = re.compile(f"({patterns['nome'].pattern})" + r".{0,80}?" + f"({patterns['oab'].pattern})")
        resultados.extend(padrao_completo.finditer(texto_norm))
    else:
        resultados.extend(patterns['nome'].finditer(texto_norm))
    return resultados

def extract_text_from_page(page) -> str:
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
    cols = set(c.name for c in model_cls.__table__.columns)
    return {k: v for k, v in kwargs.items() if k in cols}

# ===================== WHATSAPP OTIMIZADO E PARALELO =====================
def enviar_whatsapp_single(telefone: str, mensagem: str) -> bool:
    if not telefone: return False
    try:
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        headers = {"Content-Type": "application/json", "sessionkey": "oab"}
        payload = {"session": "oab", "number": telefone, "text": mensagem}
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            logger.info(f"Mensagem enviada para {telefone}")
            return True
        else:
            logger.error(f"Erro WhatsApp ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Erro WhatsApp: {e}")
        return False

def enviar_notificacao_individual(mencoes: list, dt: date, caderno: str) -> int:
    """Envia mensagem WhatsApp individual com opção de CANCELAR."""
    advogado = mencoes[0]["advogado"]
    if not getattr(advogado, "whatsapp", None): 
        return 0
    
    qtd_mencoes = len(mencoes)
    palavra_mencao = "menção" if qtd_mencoes == 1 else "menções"
    
    # Emojis por caderno
    CADERNO_EMOJIS = {
        "E": "📘",
        "ADMINISTRATIVO": "📗", 
        "JUDICIARIO": "📕"
    }
    emoji_caderno = CADERNO_EMOJIS.get(caderno.upper(), "📋")
    
    # Cria dicionário de links únicos por página
    paginas_links = {m["pagina"]: m["link"] for m in mencoes}
    paginas = sorted(paginas_links.keys())
    
    # Construção da mensagem
    mensagem = (
        f"{emoji_caderno} *RECORTE DIGITAL - OAB/RJ* {emoji_caderno}\n"
        f"{'-'*40}\n\n"
        f"📌 *Advogado:* {advogado.nome_completo}\n"
        f"📅 *Diário Oficial:* {dt.strftime('%d/%m/%Y')}\n"
        f"🗂️ *Caderno:* {caderno}\n"
        f"• *{qtd_mencoes} {palavra_mencao}*\n"
        f"• *Páginas:* {', '.join(map(str, paginas))}\n\n"
    )
    
    # Exemplos das menções (máximo 2)
    if len(mencoes) > 0:
        mensagem += "*📖 PRINCIPAIS MENCÕES:*\n"
        for i, mencao in enumerate(mencoes[:2], 1):
            contexto_limpo = mencao["contexto"].replace('"', '').replace('*', '').strip()
            mensagem += f"*{i}. Pág. {mencao['pagina']}:*\n"
            mensagem += f'"{contexto_limpo[:160]}{"..." if len(contexto_limpo) > 160 else ""}"\n\n'
    
    # Links diretos (máximo 5)
    mensagem += "*🔗 LINKS DIRETOS:*\n"
    for pagina, link in list(paginas_links.items())[:5]:
        mensagem += f"• 📄 Pág. {pagina}: {link}\n"
    if len(paginas_links) > 5:
        mensagem += f"• ... e mais {len(paginas_links) - 5} páginas\n"
    
    # Rodapé com opção de cancelamento
    mensagem += (
        f"{'-'*40}\n"
        f"📢 *Recorte Digital OAB/RJ*\n"
        f"Receba suas publicações de forma rápida e prática.\n\n"
        f"❌ Caso não deseje mais receber este serviço, responda *CANCELAR* a este WhatsApp.\n"
        f"*🤝 EQUIPE OAB/RJ*"
    )
    
    if enviar_whatsapp_single(advogado.whatsapp, mensagem):
        return 1
    return 0

def enviar_notificacoes_paralelo(por_advogado: dict, dt: date, caderno: str) -> int:
    """Envia notificações em paralelo com ThreadPoolExecutor."""
    total_msgs = 0
    with ThreadPoolExecutor(max_workers=WHATSAPP_THREADS) as executor:
        futures = [executor.submit(enviar_notificacao_individual, mencoes, dt, caderno) 
                  for mencoes in por_advogado.values() if mencoes]
        
        for future in futures:
            try:
                total_msgs += future.result()
                time.sleep(1.5)  # Pausa para não sobrecarregar a API
            except Exception as e:
                logger.error(f"Erro ao enviar notificação: {e}")
    
    logger.info(f"Notificações paralelas enviadas: {total_msgs}")
    return total_msgs

# ===================== DOWNLOAD COM SOLUÇÃO HÍBRIDA =====================
def baixar_pdf_durante_sessao(dt: date, caderno: str, driver: webdriver.Chrome) -> str | None:
    destino = caminho_pdf_cache(dt, caderno)
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        size_mb = os.path.getsize(destino) / (1024 * 1024)
        logger.info(f"Cache encontrado ({size_mb:.1f}MB): {destino}")
        return destino
    logger.info(f"Buscando PDF para {dt.strftime('%d/%m/%Y')} [caderno={caderno}]...")

    for tentativa in range(MAX_RETRIES):
        try:
            url = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina=-1"
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            iframes = WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
            
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                if "pdf.aspx" not in src: continue
                try:
                    WebDriverWait(driver, 15).until(EC.frame_to_be_available_and_switch_to_it(iframe))
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(2)
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
                    session = requests.Session()
                    for c in driver.get_cookies():
                        try: session.cookies.set(c["name"], c["value"])
                        except Exception: pass
                    headers = {
                        "User-Agent": USER_AGENT, 
                        "Accept": "application/pdf, */*", 
                        "Referer": driver.current_url, 
                        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
                    }
                    for path in candidates:
                        clean_path = path.lstrip("/").replace("consultadje/", "").strip()
                        if not clean_path.lower().startswith("temp/"): 
                            clean_path = f"temp/{clean_path}"
                        pdf_url = f"https://www3.tjrj.jus.br/consultadje/{clean_path}"
                        logger.info(f"🎯 Tentando URL: {pdf_url}")
                        try:
                            response = session.get(pdf_url, headers=headers, timeout=30)
                            if response.status_code == 200 and response.content.startswith(b"%PDF"):
                                os.makedirs(os.path.dirname(destino), exist_ok=True)
                                with open(destino, "wb") as f: 
                                    f.write(response.content)
                                size_mb = len(response.content) / (1024 * 1024)
                                logger.info(f"💾 PDF salvo ({size_mb:.1f}MB): {destino}")
                                return destino
                        except Exception as e:
                            logger.warning(f"Falha ao baixar candidato: {e}")
                    driver.switch_to.default_content()
                except TimeoutException:
                    logger.warning("Timeout ao acessar iframe. Continuando...")
                    driver.switch_to.default_content()
                    continue
                except Exception as e:
                    logger.warning(f"Erro no iframe: {e}")
                    driver.switch_to.default_content()
                    continue
            logger.warning(f"Tentativa {tentativa+1}/{MAX_RETRIES} falhou para o caderno {caderno}. Tentando novamente em 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Erro na tentativa {tentativa+1}/{MAX_RETRIES} para o caderno {caderno}: {e}. Tentando novamente em 5s...")
            time.sleep(5)
    logger.error(f"❌ Falha crítica: não foi possível baixar PDF após {MAX_RETRIES} tentativas. Abortando.")
    return None

def processar_pdf(dt: date, caderno: str, caminho_pdf: str, advogados: List[Advogado]) -> Tuple[int, Dict[int, List[Dict]]]:
    total_mencoes = 0
    por_advogado = defaultdict(list)

    # Pré-compila padrões para todos os advogados
    for advogado in advogados:
        if advogado.id not in advogado_patterns:
            advogado_patterns[advogado.id] = {
                'nome': criar_regex_nome_flexivel(advogado.nome_completo),
                'oab': criar_regex_oab(advogado.numero_oab) if advogado.numero_oab else None
            }

    logger.info(f"Processando {len(advogados)} advogados no caderno {caderno}...")
    with open(caminho_pdf, "rb") as fp:
        for page_num, page in enumerate(PDFPage.get_pages(fp), 1):
            try:
                raw_text = extract_text_from_page(page)
                if not raw_text or len(raw_text.strip()) < 50:
                    logger.debug(f"Página {page_num} vazia ou muito curta. Pulando.")
                    continue
                texto_norm = normalizar_texto(raw_text)
                
                for advogado in advogados:
                    patterns = advogado_patterns[advogado.id]
                    if patterns['oab']:
                        padrao_completo = re.compile(f"({patterns['nome'].pattern})" + r".{0,80}?" + f"({patterns['oab'].pattern})")
                        matches = padrao_completo.finditer(texto_norm)
                    else:
                        matches = patterns['nome'].finditer(texto_norm)
                    
                    for match in matches:
                        total_mencoes += 1
                        start, end = match.span()
                        ctx_ini = max(0, start - 120)
                        ctx_fim = min(len(texto_norm), end + 120)
                        contexto = texto_norm[ctx_ini:ctx_fim].strip()
                        link_publicacao = f"https://www3.tjrj.jus.br/consultadje/consultaDJE.aspx?dtPub={dt.strftime('%d/%m/%Y')}&caderno={caderno}&pagina={page_num}"
                        mencao = {
                            "advogado": advogado, 
                            "pagina": page_num, 
                            "contexto": contexto, 
                            "link": link_publicacao,
                            "data_publicacao": dt, 
                            "caderno": caderno,
                        }
                        por_advogado[advogado.id].append(mencao)
                        logger.info(f"Menção confirmada: {advogado.nome_completo} - Página {page_num}")
                
                if page_num % 10 == 0: 
                    logger.info(f"Páginas processadas: {page_num}")
            except Exception as e:
                logger.error(f"Erro ao processar página {page_num}: {e}")
                continue
    return total_mencoes, dict(por_advogado)

def persistir_resultados(dt: date, caderno: str, caminho_pdf: str, total_mencoes: int, por_advogado: dict):
    q = DiarioOficial.query.filter_by(data_publicacao=dt)
    if "caderno" in (c.name for c in DiarioOficial.__table__.columns): 
        q = q.filter_by(caderno=caderno)
    if q.first():
        logger.warning(f"Diário já existente. Pulando persistência.")
        return None
    try:
        diario_kwargs = _filter_kwargs(
            DiarioOficial, 
            data_publicacao=dt, 
            fonte="DJERJ", 
            caderno=caderno, 
            total_publicacoes=total_mencoes, 
            arquivo_pdf=caminho_pdf
        )
        diario = DiarioOficial(**diario_kwargs)
        db.session.add(diario)
        db.session.flush()
        
        publicacoes_a_inserir = []
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
                    mensagem=f"Menção na página {m['pagina']}", 
                    link=m["link"], 
                    qtd_mencoes=1
                )
                publicacoes_a_inserir.append(pub_kwargs)
        
        if publicacoes_a_inserir: 
            db.session.bulk_insert_mappings(AdvogadoPublicacao, publicacoes_a_inserir)
        db.session.commit()
        logger.info(f"Diário persistido: {dt.strftime('%d/%m/%Y')} [{caderno}] – {total_mencoes} menções")
        return diario
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao persistir: {e}")
        return None

def processar_caderno_do_dia(dt: date, caderno: str, advogados: List[Advogado], driver: webdriver.Chrome) -> Tuple[int, int]:
    logger.info(f"\n===== CADERNO: {caderno} =====")
    q = DiarioOficial.query.filter_by(data_publicacao=dt)
    if "caderno" in (c.name for c in DiarioOficial.__table__.columns): 
        q = q.filter_by(caderno=caderno)
    if q.first():
        logger.warning(f"Diário já processado para {dt.strftime('%d/%m/%Y')} [{caderno}]. Pulando.")
        return 0, 0
    
    caminho = baixar_pdf_durante_sessao(dt, caderno, driver)
    if not caminho:
        logger.error(f"Falha ao obter PDF para caderno {caderno}")
        return 0, 0
    
    total_mencoes, por_advogado = processar_pdf(dt, caderno, caminho, advogados)
    if total_mencoes == 0:
        logger.info("Nenhuma menção encontrada. Pulando persistência.")
        return 0, 0
    
    diario = persistir_resultados(dt, caderno, caminho, total_mencoes, por_advogado)
    if not diario: 
        return 0, 0
    
    msgs_enviadas = enviar_notificacoes_paralelo(por_advogado, dt, caderno)
    return total_mencoes, msgs_enviadas

# ===================== ORQUESTRAÇÃO TURBINADA =====================
def executar_scraper_completo():
    agora_sp = datetime.now(TZ_SP)
    dt = agora_sp.date()
    inicio = time.time()
    logger.info(f"Processando DJERJ de {dt.strftime('%d/%m/%Y')}")
    
    advogados = Advogado.query.all()
    logger.info(f"📊 {len(advogados)} advogados carregados")
    
    cadernos = obter_cadernos()
    logger.info(f"Cadernos: {', '.join(cadernos)}")
    
    total_geral_mencoes = 0
    total_geral_msgs = 0

    # Configuração única do Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-agent={USER_AGENT}")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        for caderno in cadernos:
            try:
                mencoes, msgs = processar_caderno_do_dia(dt, caderno, advogados, driver)
                total_geral_mencoes += mencoes
                total_geral_msgs += msgs
            except Exception as e:
                logger.error(f"Erro ao processar caderno {caderno}: {e}")
                continue
    except Exception as e:
        logger.error(f"Erro geral na execução: {e}")
    finally:
        driver.quit()

    dur = time.time() - inicio
    logger.info("="*50)
    logger.info(f"✅ Concluído em {dur:.2f}s | Menções: {total_geral_mencoes} | Notificações: {total_geral_msgs}")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        executar_scraper_completo()
