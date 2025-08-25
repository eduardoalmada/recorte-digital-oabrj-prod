# app/scripts/teste_whatsapp.py
import os
import requests
from app import create_app
from app.models import Advogado

def teste_whatsapp():
    app = create_app()
    
    with app.app_context():
        # Buscar o advogado
        advogado = Advogado.query.filter_by(numero_oab="OAB/RJ-012686").first()
        
        if not advogado:
            print("❌ Advogado não encontrado")
            return
        
        mensagem = (
            f"Olá, {advogado.nome_completo}. "
            "TESTE: Mensagem de teste do sistema Recorte Digital OABRJ."
        )
        
        print(f"📞 Testando WhatsApp para: {advogado.whatsapp}")
        print(f"📝 Mensagem: {mensagem}")
        
        # Função de envio (igual ao scraper)
        url = os.getenv("WHATSAPP_API_URL", "https://oabrj.uzapi.com.br:3333/sendText")
        payload = {
            "session": "oab",
            "sessionkey": "oab",  # ← Verificar essa sessionkey!
            "to": advogado.whatsapp,
            "text": mensagem,
        }
        
        print(f"🔗 URL: {url}")
        print(f"📦 Payload: {payload}")
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            print(f"📨 Resposta: {response.status_code} - {response.text}")
            
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    teste_whatsapp()
