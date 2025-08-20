# app/scrapers/verificador_advogados_djerj.py
import requests
import pdfplumber
import re
from datetime import datetime, date
from app import db
from app.models.advogado import Advogado
from app.models.diario_oficial import DiarioOficial

def verificar_advogados_diario_hoje():
    """Verifica quais advogados aparecem no diário de hoje"""
    hoje = date.today()
    print(f"🔍 Verificando advogados no diário de {hoje}")
    
    # Busca o diário de hoje
    diario = DiarioOficial.query.filter_by(data_publicacao=hoje).first()
    
    if not diario:
        print(f"❌ Nenhum diário encontrado para {hoje}")
        print("💡 Execute primeiro: python -m app.scrapers.scraper_djerj_selenium")
        return
    
    print(f"📰 Diário encontrado: {diario.arquivo_pdf}")
    
    # Busca todos os advogados do banco
    advogados = Advogado.query.all()
    print(f"👨‍💼 Total de advogados no banco: {len(advogados)}")
    
    if not advogados:
        print("❌ Nenhum advogado cadastrado no banco")
        print("💡 Adicione advogados na tabela 'advogado'")
        return
    
    # Baixa o PDF
    pdf_path = f"/tmp/diario_{hoje}.pdf"
    print("📥 Baixando PDF...")
    
    try:
        response = requests.get(diario.arquivo_pdf, timeout=30)
        response.raise_for_status()
        
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
        
        print("✅ PDF baixado com sucesso")
        
    except Exception as e:
        print(f"❌ Erro ao baixar PDF: {e}")
        return
    
    # Extrai texto do PDF
    print("📖 Extraindo texto do PDF...")
    texto_completo = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                texto = page.extract_text()
                if texto:
                    texto_completo += texto + "\n"
                print(f"📄 Página {i+1} processada")
        
        print(f"✅ Texto extraído: {len(texto_completo)} caracteres")
        
    except Exception as e:
        print(f"❌ Erro ao extrair texto do PDF: {e}")
        return
    
    # Busca advogados no texto
    print("🔎 Buscando advogados no texto...")
    advogados_encontrados = []
    
    for advogado in advogados:
        # Busca pelo nome (case insensitive)
        if advogado.nome_completo.lower() in texto_completo.lower():
            advogados_encontrados.append(advogado)
            print(f"✅ ENCONTRADO: {advogado.nome_completo}")
            continue
        
        # Busca pela OAB
        padroes_oab = [
            f"OAB/RJ {advogado.numero_oab}",
            f"OAB RJ {advogado.numero_oab}",
            f"OAB{advogado.numero_oab}",
            f"OAB.{advogado.numero_oab}",
        ]
        
        for padrao in padroes_oab:
            if padrao in texto_completo:
                advogados_encontrados.append(advogado)
                print(f"✅ ENCONTRADO pela OAB: {advogado.nome_completo}")
                break
    
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
    else:
        print("\n😞 Nenhum advogado encontrado no diário de hoje")

if __name__ == "__main__":
    verificar_advogados_diario_hoje()
