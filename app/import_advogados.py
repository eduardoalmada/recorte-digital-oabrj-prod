import csv
import os
from app import create_app, db
from app.models import Advogado

# Caminho relativo do CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'lista-adv-oab-geral.csv')

app = create_app()

with app.app_context():
    with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
       reader = csv.DictReader(csvfile, delimiter=';')
        first_row = next(reader)
        print("📄 Primeira linha do CSV:", first_row)
        csvfile.seek(0)  # volta pro início do arquivo
        next(reader)  # pula o cabeçalho de novo

        for row in reader:
            advogado = Advogado(
                nome_completo=row['nome_completo'],
                numero_oab=row['numero_oab'],
                whatsapp=row.get('whatsapp'),
                email=row.get('email')
            )
            db.session.add(advogado)
        db.session.commit()

    print("✅ Dados importados com sucesso.")
