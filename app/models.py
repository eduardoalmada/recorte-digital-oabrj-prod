from app import db
from datetime import datetime

class Advogado(db.Model):
    __tablename__ = "advogado"

    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(255), nullable=False)
    numero_oab = db.Column(db.String(50), nullable=True)
    whatsapp = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com publicações
    publicacoes = db.relationship('AdvogadoPublicacao', backref='advogado', lazy=True)


class DiarioOficial(db.Model):
    __tablename__ = "diario_oficial"

    id = db.Column(db.Integer, primary_key=True)
    data_publicacao = db.Column(db.Date, nullable=False, unique=True, index=True)
    fonte = db.Column(db.String(100), default="DJERJ", nullable=False)
    total_publicacoes = db.Column(db.Integer, default=0)
    arquivo_pdf = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com publicações de advogados
    publicacoes_advogados = db.relationship('AdvogadoPublicacao', backref='diario', lazy=True)


class AdvogadoPublicacao(db.Model):
    __tablename__ = "advogado_publicacao"  # Nome da tabela de relacionamento

    id = db.Column(db.Integer, primary_key=True)
    advogado_id = db.Column(db.Integer, db.ForeignKey('advogado.id'), nullable=False)
    diario_id = db.Column(db.Integer, db.ForeignKey('diario_oficial.id'), nullable=False)
    data_publicacao = db.Column(db.Date, nullable=False)
    qtd_mencoes = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Mantenha a tabela Publicacao original se ainda for usada para outras finalidades
class Publicacao(db.Model):
    __tablename__ = "publicacao"

    id = db.Column(db.Integer, primary_key=True)
    advogado_id = db.Column(
        db.Integer, db.ForeignKey("advogado.id", ondelete="CASCADE"), nullable=False
    )
    quantidade_publicacoes = db.Column(db.Integer, default=1)
    titulo = db.Column(db.String(500), nullable=False)
    data_disponibilizacao = db.Column(db.Date, nullable=True)
    data_publicacao = db.Column(db.Date, nullable=False)
    tribunal = db.Column(db.String(255), nullable=True)
    jornal = db.Column(db.String(255), nullable=True)
    caderno = db.Column(db.String(255), nullable=True)
    numero_pagina = db.Column(db.String(50), nullable=True)
    local = db.Column(db.String(255), nullable=True)
    mensagem = db.Column(db.Text, nullable=True)
    link = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
