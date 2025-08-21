import os
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("🔧 Corrigindo schema do banco...")
    
    try:
        # 1. Adiciona a coluna pdf_url se não existir
        db.session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'diarios_oficiais' AND column_name = 'pdf_url') THEN
                    ALTER TABLE diarios_oficiais ADD COLUMN pdf_url VARCHAR(500);
                    RAISE NOTICE 'Coluna pdf_url adicionada com sucesso';
                ELSE
                    RAISE NOTICE 'Coluna pdf_url já existe';
                END IF;
            END $$;
        """))
        print("✅ Coluna pdf_url verificada/adicionada")
        
        # 2. Remove tabelas antigas se existirem (com CASCADE para evitar erros de dependência)
        db.session.execute(text("DROP TABLE IF EXISTS html_djerj_raw CASCADE"))
        print("✅ Tabela html_djerj_raw removida (se existia)")
        
        # 3. Cria índices se não existirem
        db.session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_diarios_data_publicacao') THEN
                    CREATE INDEX idx_diarios_data_publicacao ON diarios_oficiais(data_publicacao);
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_publicacao_data') THEN
                    CREATE INDEX idx_publicacao_data ON publicacao(data);
                END IF;
            END $$;
        """))
        print("✅ Índices verificados/criados")
        
        db.session.commit()
        print("🎉 Schema corrigido com sucesso!")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao corrigir schema: {e}")
