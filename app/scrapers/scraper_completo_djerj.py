import requests
from datetime import datetime
import re
from bs4 import BeautifulSoup
import time

def baixar_pdf_djerj_completo(data):
    """
    Fluxo completo:
    1. Acessa a página inicial
    2. Clica no botão "Visualizar a Íntegra"
    3. Acessa a página com o iframe do PDF
    4. Extrai a URL do PDF do iframe
    5. Baixa o PDF
    """
    
    # Headers para simular navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Criar sessão para manter cookies
    session = requests.Session()
    
    try:
        # 1. Acessar página inicial
        print("🌐 Acessando página inicial...")
        url_inicial = "https://www3.tjrj.jus.br/consultadje/"
        response_inicial = session.get(url_inicial, headers=headers, timeout=30)
        response_inicial.raise_for_status()
        
        # 2. Extrair ViewState e outros campos do formulário
        soup = BeautifulSoup(response_inicial.text, 'html.parser')
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value'] if soup.find('input', {'name': '__VIEWSTATE'}) else ''
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value'] if soup.find('input', {'name': '__VIEWSTATEGENERATOR'}) else ''
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value'] if soup.find('input', {'name': '__EVENTVALIDATION'}) else ''
        
        # 3. Simular clique no botão "Visualizar a Íntegra"
        print("🖱️  Simulando clique no botão...")
        url_post = "https://www3.tjrj.jus.br/consultadje/"
        
        data_post = {
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstate_generator,
            '__EVENTVALIDATION': event_validation,
            'ctl00$ContentPlaceHolder1$btnVisIntegra': 'Visualizar a Íntegra Do Caderno V - Editais e demais publicações'
        }
        
        response_post = session.post(url_post, data=data_post, headers=headers, timeout=30)
        response_post.raise_for_status()
        
        # 4. Extrair URL do iframe do PDF
        print("🔍 Procurando iframe do PDF...")
        iframe_pattern = r'<iframe[^>]+src="([^"]+)"'
        iframe_match = re.search(iframe_pattern, response_post.text)
        
        if iframe_match:
            iframe_url = iframe_match.group(1)
            print(f"📄 Iframe encontrado: {iframe_url}")
            
            # 5. Extrair nome do arquivo PDF
            if 'filename=' in iframe_url:
                pdf_filename = iframe_url.split('filename=')[1]
                pdf_direct_url = f"https://www3.tjrj.jus.br/consultadje/temp/{pdf_filename}"
                
                print(f"⬇️  Baixando PDF: {pdf_direct_url}")
                
                # 6. Baixar o PDF
                pdf_response = session.get(pdf_direct_url, headers=headers, timeout=60)
                pdf_response.raise_for_status()
                
                return pdf_response.content
            else:
                print("❌ Nome do arquivo PDF não encontrado no iframe")
                return None
        else:
            print("❌ Iframe do PDF não encontrado")
            return None
            
    except Exception as e:
        print(f"❌ Erro no processo: {e}")
        return None

# Função para usar no seu scraper principal
def executar_scraper_atualizado():
    hoje = datetime.now().date()
    
    print(f"📅 Verificando Diário Oficial de {hoje.strftime('%d/%m/%Y')}")
    
    # Verificar se já foi processado hoje
    if DiarioOficial.query.filter_by(data_publicacao=hoje).first():
        print(f"✅ Diário de {hoje.strftime('%d/%m/%Y')} já processado")
        return
    
    # Baixar PDF
    pdf_content = baixar_pdf_djerj_completo(hoje)
    
    if pdf_content:
        # Salvar PDF e processar
        nome_arquivo = f"diario_{hoje.strftime('%Y%m%d')}.pdf"
        caminho_pdf = os.path.join('temp', nome_arquivo)
        
        with open(caminho_pdf, 'wb') as f:
            f.write(pdf_content)
        
        print(f"💾 PDF salvo: {caminho_pdf}")
        
        # Extrair texto do PDF (usando pdfminer)
        texto = extrair_texto_pdf(caminho_pdf)
        
        # Processar texto e salvar no banco
        processar_diario(texto, hoje, caminho_pdf)
        
        # Limpar arquivo temporário
        os.remove(caminho_pdf)
        
    else:
        print("❌ Nenhum PDF encontrado para download")

# No seu scraper principal, substitua a chamada atual por:
# executar_scraper_atualizado()
