from app import db

class Advogado(db.Model):
    __tablename__ = 'advogado'  # define explicitamente o nome da tabela

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
    link = db.Column(db.String(255), nullable=False)
    data = db.Column(db.Date, nullable=False)
    notificado = db.Column(db.Boolean, default=False)
