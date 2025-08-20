from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Advogado(db.Model):
    __tablename__ = "advogados"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False, unique=False)
    numero_oab = db.Column(db.String(50), nullable=True)
    telefone = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Advogado {self.nome}>"


class Publicacao(db.Model):
    __tablename__ = "publicacoes"

    id = db.Column(db.Integer, primary_key=True)
    advogado_id = db.Column(db.Integer, db.ForeignKey("advogados.id"), nullable=False)
    nome_advogado = db.Column(db.String(255), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.Date, nullable=False, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    advogado = db.relationship("Advogado", backref=db.backref("publicacoes", lazy=True))

    def __repr__(self):
        return f"<Publicacao {self.nome_advogado} - {self.data_publicacao}>"


class DiarioOficial(db.Model):
    __tablename__ = "diarios_oficiais"

    id = db.Column(db.Integer, primary_key=True)
    data_publicacao = db.Column(db.Date, nullable=False, unique=True, index=True)
    fonte = db.Column(db.String(100), default="DJERJ")
    arquivo_pdf = db.Column(db.LargeBinary, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DiarioOficial {self.data_publicacao} - {self.fonte}>"
