import csv
import os
from app import app
from app.models import db, Advogado

# Caminho relativo para o arquivo CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'lista-adv-oab-geral.csv')

with app.app_context():
    with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
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
