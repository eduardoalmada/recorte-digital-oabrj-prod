from flask import Blueprint, request, jsonify
from app.models import Advogado, AdvogadoExcluido
from app.extensions import db
from datetime import datetime

webhook_bp = Blueprint("webhook", __name__)

@webhook_bp.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    # Estrutura típica do UZAPI:
    # {
    #   "phone": "5521999999999",
    #   "message": "CANCELAR"
    # }
    telefone = data.get("phone")
    mensagem = data.get("message", "").strip().upper()

    if not telefone:
        return jsonify({"status": "error", "msg": "Telefone não informado"}), 400

    if mensagem == "CANCELAR":
        advogado = Advogado.query.filter_by(telefone=telefone).first()
        if not advogado:
            return jsonify({"status": "ok", "msg": "Número não encontrado na base."})

        # Move para advogados_excluidos
        advogado_excluido = AdvogadoExcluido(
            nome_completo=advogado.nome_completo,
            numero_oab=advogado.numero_oab,
            telefone=advogado.telefone,
            data_exclusao=datetime.now()
        )
        db.session.add(advogado_excluido)
        db.session.delete(advogado)
        db.session.commit()

        return jsonify({"status": "ok", "msg": "Número removido com sucesso."})

    return jsonify({"status": "ok", "msg": "Mensagem recebida, mas não é CANCELAR."})
