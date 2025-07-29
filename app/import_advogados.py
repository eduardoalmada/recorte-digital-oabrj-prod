import csv
import os
from app import create_app, db
from app.models import Advogado

# Caminho relativo do CSV corrigido
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'lista-adv-oab-geral.csv')

app = create_app()

with app.app_context():
    with open(CSV_PATH, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')

        # Mostra a primeira linha lida
        first_row = next(reader)
        print("📄 Primeira linha do CSV:", first_row)

        # Reposiciona o ponteiro e pula o cabeçalho
        csvfile.seek(0)
        next(reader)

        count = 0
        for row in reader:
            try:
                advogado = Advogado(
                    nome_completo=row['nome_completo'].strip(),
                    numero_oab=row['numero_oab'].strip(),
                    whatsapp=row.get('whatsapp', '').strip(),
                    email=row.get('email', '').strip()
                )
                db.session.add(advogado)
                count += 1
            except Exception as e:
                print(f"⚠️ Erro na linha {count + 2}: {e}")  # +2 porque pulou o cabeçalho

        db.session.commit()
        print(f"✅ {count} advogados importados com sucesso.")
