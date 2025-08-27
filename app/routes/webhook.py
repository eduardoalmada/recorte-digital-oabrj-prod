from flask import Blueprint, request, jsonify
from app import db
from app.models import Advogado
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Table, Column, Integer, String, MetaData

# Cria blueprint
webhook_bp = Blueprint("webhook", __name__)

# Define tabela advogados_excluidos manualmente
metadata = db.metadata

AdvogadosExcluidos = Table(
    "advogados_excluidos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome_completo", String, nullable=False),
    Column("numero_oab", String, nullable=True),
    Column("whatsapp", String, nullable=False),
)

@webhook_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Webhook que recebe mensagens do WhatsApp (via UZAPI).
    Se o usuário responder 'CANCELAR', remove da tabela advogados e
    insere em advogados_excluidos.
    """
    try:
        data = request.get_json()
        numero = data.get("phone")  # formato: 5521999999999
        mensagem = data.get("message", "").strip().upper()

        if not numero or not mensagem:
            return jsonify({"error": "Dados inválidos"}), 400

        # Só trata mensagem "CANCELAR"
        if mensagem == "CANCELAR":
            advogado = Advogado.query.filter_by(whatsapp=numero).first()
            if not advogado:
                return jsonify({"status": "whatsapp não encontrado"}), 404

            # Insere no advogados_excluidos
            insert_stmt = AdvogadosExcluidos.insert().values(
                nome_completo=advogado.nome_completo,
                numero_oab=advogado.numero_oab,
                whatsapp=advogado.whatsapp,
            )
            db.session.execute(insert_stmt)

            # Remove da tabela advogados
            db.session.delete(advogado)
            db.session.commit()

            return jsonify({"status": "advogado removido e movido para advogados_excluidos"}), 200

        return jsonify({"status": "mensagem ignorada"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
