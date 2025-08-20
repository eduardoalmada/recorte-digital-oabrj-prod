# app/scrapers/verificador_advogados_djerj.py
import requests
import pdfplumber
import re
from datetime import datetime, date
from app import db
from app.models.advogado import Advogado
from app.models.diario_oficial import DiarioOficial

def baixar_pdf(url, caminho_destino):
    """Baixa o PDF e salva localmente"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(caminho_destino, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ PDF baixado: {caminho_destino}")
        return True
    except Exception as e:
        print(f"❌ Erro ao baixar PDF: {e}")
        return False

def extrair_texto_pdf(caminho_pdf):
    """Extrai texto do PDF"""
    texto_completo = ""
    try:
        with pdfplumber.open(caminho_pdf) as pdf:
            for i, page in enumerate(pdf.pages):
                texto = page.extract_text()
                if texto:
                    texto_completo += texto + "\n"
                print(f"📄 Página {i+1} processada")
        
        return texto_completo
    except Exception as e:
        print(f"❌ Erro ao extrair texto do PDF: {e}")
        return ""

def buscar_advogados_no_texto(texto, advogados):
    """Busca advogados no texto extraído"""
    encontrados = []
    
    for advogado in advogados:
        # Busca pelo nome (case insensitive)
        nome_pattern = re.compile(re.escape(advogado.nome_completo), re.IGNORECASE)
        if nome_pattern.search(texto):
            encontrados.append(advogado)
            print(f"✅ ENCONTRADO: {advogado.nome_completo}")
            continue
        
        # Busca pela OAB (formatos: OAB/RJ 123456, OAB RJ 123456, etc.)
        oab_patterns = [
            f"OAB/RJ {advogado.numero_oab}",
            f"OAB RJ {advogado.numero_oab}",
            f"OAB{advogado.numero_oab}",
            f"OAB.{advogado.numero_oab}",
        ]
        
        for pattern in oab_patterns:
            if pattern in texto:
                encontrados.append(advogado)
                print(f"✅ ENCONTRADO pela OAB: {advogado.nome_completo} - {advogado.numero_oab}")
                break
    
    return encontrados

def verificar_advogados_diario_hoje():
    """Verifica quais advogados aparecem no diário de hoje"""
    hoje = date.today()
    print(f"🔍 Verificando advogados no diário de {hoje}")
    
    # Busca o diário de hoje
    diario = DiarioOficial.query.filter_by(data_publicacao=hoje).first()
    
    if not diario:
        print(f"❌ Nenhum diário encontrado para {hoje}")
        return
    
    print(f"📰 Diário encontrado: {diario.arquivo_pdf}")
    
    # Busca todos os advogados do banco
    advogados = Advogado.query.all()
    print(f"👨‍💼 Total de advogados no banco: {len(advogados)}")
    
    if not advogados:
        print("❌ Nenhum advogado cadastrado no banco")
        return
    
    # Baixa o PDF
    pdf_path = f"/tmp/diario_{hoje}.pdf"
    if not baixar_pdf(diario.arquivo_pdf, pdf_path):
        return
    
    # Extrai texto do PDF
    texto = extrair_texto_pdf(pdf_path)
    if not texto:
        print("❌ Não foi possível extrair texto do PDF")
        return
    
    print(f"📝 Texto extraído: {len(texto)} caracteres")
    
    # Busca advogados no texto
    advogados_encontrados = buscar_advogados_no_texto(texto, advogados)
    
    # Exibe resultados
    print("\n" + "="*50)
    print("🎯 RESULTADO DA BUSCA")
    print("="*50)
    print(f"📊 Total de advogados no banco: {len(advogados)}")
    print(f"✅ Advogados encontrados no diário: {len(advogados_encontrados)}")
    print(f"❌ Advogados não encontrados: {len(advogados) - len(advogados_encontrados)}")
    
    if advogados_encontrados:
        print("\n📋 Advogados encontrados:")
        for adv in advogados_encontrados:
            print(f"   • {adv.nome_completo} - OAB/RJ {adv.numero_oab}")
    
    # Salva log no banco (opcional)
    salvar_resultado_busca(hoje, len(advogados_encontrados))

def salvar_resultado_busca(data, quantidade_encontrados):
    """Salva o resultado da busca (opcional)"""
    try:
        # Você pode criar uma tabela para logs se quiser
        print(f"📊 Resultado: {quantidade_encontrados} advogados encontrados em {data}")
    except Exception as e:
        print(f"⚠️ Erro ao salvar log: {e}")

def verificar_advogados_diario_especifico(data):
    """Verifica advogados em uma data específica"""
    diario = DiarioOficial.query.filter_by(data_publicacao=data).first()
    if diario:
        print(f"🔍 Verificando diário de {data}")
        # Adapte a função principal para receber a data
    else:
        print(f"❌ Nenhum diário encontrado para {data}")

if __name__ == "__main__":
    verificar_advogados_diario_hoje()
