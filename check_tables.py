import os
from app import create_app, db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    # Verifica tabelas existentes
    inspector = inspect(db.engine)
    print("📋 Tabelas existentes:")
    for table in inspector.get_table_names():
        print(f"  - {table}")
        for column in inspector.get_columns(table):
            print(f"    ↳ {column['name']} ({column['type']})")
    
    # Verifica se a coluna pdf_url existe em diarios_oficiais
    try:
        result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'diarios_oficiais' AND column_name = 'pdf_url'"))
        if result.fetchone():
            print("✅ Coluna pdf_url já existe em diarios_oficiais")
        else:
            print("❌ Coluna pdf_url NÃO existe em diarios_oficiais")
    except Exception as e:
        print(f"❌ Erro ao verificar colunas: {e}")
