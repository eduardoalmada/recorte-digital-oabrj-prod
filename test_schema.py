import os
from app import create_app, db
from app.models import DiarioOficial
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("🧪 Testando schema...")
    
    # Testa se a coluna pdf_url existe e funciona
    try:
        # Tenta criar um registro de teste
        test_record = DiarioOficial(
            fonte="TESTE",
            data_publicacao="2025-08-21",
            pdf_url="http://teste.com/documento.pdf"
        )
        db.session.add(test_record)
        db.session.commit()
        print("✅ Teste de escrita bem-sucedido")
        
        # Limpa o registro de teste
        db.session.delete(test_record)
        db.session.commit()
        print("✅ Teste de limpeza bem-sucedido")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro no teste: {e}")
