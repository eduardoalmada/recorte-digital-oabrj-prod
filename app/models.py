from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Advogado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String, nullable=False)
    numero_oab = db.Column(db.String, nullable=False)
    whatsapp = db.Column(db.String)
    email = db.Column(db.String)

class Publicacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    advogado_id = db.Column(db.Integer, db.ForeignKey('advogado.id'))
    titulo = db.Column(db.String)
    descricao = db.Column(db.Text)
    link = db.Column(db.String)
    data = db.Column(db.Date)
