from datetime import datetime, date
from app import db

# Mantém seu schema original para não quebrar nada já existente.
class Advogado(db.Model):
    __tablename__ = 'advogado'

    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(255), nullable=False)
    numero_oab = db.Column(db.String(20), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True)

    publicacoes = db.relationship('Publicacao', backref='advogado', lazy=True)


class Publicacao(db.Model):
    __tablename__ = 'publicacao'

    id = db.Column(db.Integer, primary_key=True)
    advogado_id = db.Column(db.Integer, db.ForeignKey('advogado.id'), nullable=False)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=False)  # guardamos a URL do PDF do DJERJ aqui
    data = db.Column(db.Date, nullable=False, index=True)
    notificado = db.Column(db.Boolean, default=False)


# Tabela nova e leve para controlar o "já processei o DO de hoje?"
class DiarioOficial(db.Model):
    __tablename__ = 'diarios_oficiais'

    id = db.Column(db.Integer, primary_key=True)
    fonte = db.Column(db.String(50), nullable=False, default='DJERJ', index=True)
    data_publicacao = db.Column(db.Date, nullable=False, unique=True, index=True)
    pdf_url = db.Column(db.String(500), nullable=False)  # apenas URL (rápido e escalável)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<DiarioOficial {self.fonte} {self.data_publicacao}>"


# Índices úteis (opcional, caso use Alembic para criar depois)
#   publicacao(data), diarios_oficiais(unique data_publicacao)
