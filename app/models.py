from app import db
from datetime import datetime


class Advogado(db.Model):
    __tablename__ = "advogados"
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String, nullable=False)
    numero_oab = db.Column(db.String, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class DiarioOficial(db.Model):
    __tablename__ = "diarios_oficiais"
    id = db.Column(db.Integer, primary_key=True)
    fonte = db.Column(db.String, nullable=False)
    data_publicacao = db.Column(db.Date, nullable=False, index=True)
    arquivo_pdf = db.Column(db.String, nullable=True)  # novo campo
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class Publicacao(db.Model):
    __tablename__ = "publicacoes"
    id = db.Column(db.Integer, primary_key=True)
    advogado_id = db.Column(db.Integer, db.ForeignKey("advogados.id"), nullable=False)
    titulo = db.Column(db.String, nullable=False)
    descricao = db.Column(db.String, nullable=True)
    link = db.Column(db.String, nullable=True)
    data = db.Column(db.Date, nullable=False)
    notificado = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
