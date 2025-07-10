from flask import Blueprint, render_template
from app.models import Publicacao, Advogado

views = Blueprint('views', __name__)

@views.route("/dashboard")
def dashboard():
    pubs = (
        Publicacao.query
        .join(Advogado)
        .order_by(Publicacao.data.desc())
        .all()
    )
    return render_template("dashboard.html", publicacoes=pubs)
