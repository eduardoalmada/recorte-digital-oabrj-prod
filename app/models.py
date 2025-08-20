# app/models.py - VERSÃO CORRIGIDA
from datetime import datetime
from app import db

class Advogado(db.Model):
    __tablename__ = "advogados"

    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(255), nullable=False)  # Mudei de 'nome' para 'nome_completo'
    numero_oab = db.Column(db.String(50), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Advogado {self.nome_completo}>"

class DiarioOficial(db.Model):
    __tablename__ = "diarios_oficiais"

    id = db.Column(db.Integer, primary_key=True)
    data_publicacao = db.Column(db.Date, nullable=False, unique=True, index=True)
    fonte = db.Column(db.String(100), default="DJERJ")
    arquivo_pdf = db.Column(db.String(500), nullable=False)  # Mudei de LargeBinary para String (URL)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relação com Publicacao
    publicacoes = db.relationship('Publicacao', backref='diario', lazy=True)

    def __repr__(self):
        return f"<DiarioOficial {self.data_publicacao} - {self.fonte}>"

class Publicacao(db.Model):
    __tablename__ = "publicacoes"

    id = db.Column(db.Integer, primary_key=True)
    diario_id = db.Column(db.Integer, db.ForeignKey('diarios_oficiais.id'), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.Date, nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relação many-to-many com Advogado
    advogados = db.relationship('Advogado', secondary='publicacao_advogado', backref='publicacoes')

    def __repr__(self):
        return f"<Publicacao {self.id} - {self.data_publicacao}>"

# Tabela de associação para many-to-many
publicacao_advogado = db.Table('publicacao_advogado',
    db.Column('publicacao_id', db.Integer, db.ForeignKey('publicacoes.id'), primary_key=True),
    db.Column('advogado_id', db.Integer, db.ForeignKey('advogados.id'), primary_key=True)
)
