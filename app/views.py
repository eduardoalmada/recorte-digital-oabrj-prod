from flask import render_template
from app.models import Publicacao, Advogado

@app.route("/dashboard")
def dashboard():
    pubs = (
        Publicacao.query
        .join(Advogado)
        .order_by(Publicacao.data.desc())
        .all()
    )
    return render_template("dashboard.html", publicacoes=pubs)
