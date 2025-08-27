from flask import Blueprint, request, jsonify
from app import db
from app.models import Advogado
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

# Cria blueprint
webhook_bp = Blueprint("webhook", __name__)

# Define tabela advogados_excluidos manualmente
from sqlalchemy import Table, Column, Integer, String, MetaData

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
        if not data or "phone" not in data or "message" not in data:
            logger.warning(f"JSON inválido recebido: {data}")
            return jsonify({"error": "Dados inválidos"}), 400

        telefone = data.get("phone")  # formato: 5521999999999
        mensagem = data.get("message", "").strip().upper()

        logger.info(f"Webhook recebido para o número {telefone}: '{mensagem}'")

        # Só trata mensagem "CANCELAR"
        if mensagem == "CANCELAR":
            advogado = Advogado.query.filter_by(whatsapp=telefone).first()
            if not advogado:
                logger.info(f"Nenhum advogado encontrado com WhatsApp {telefone}")
                return jsonify({"status": "whatsapp não encontrado"}), 404

            logger.info(f"Advogado encontrado: {advogado.nome_completo} (OAB {advogado.numero_oab})")

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

            logger.info(f"Advogado {advogado.nome_completo} movido para advogados_excluidos")

            # Envia mensagem de confirmação
            from app.utils import enviar_whatsapp  # ajuste se a função estiver em outro módulo
            enviar_whatsapp(advogado.whatsapp, 
                "✅ Você foi removido do Recorte Digital OAB/RJ. Não receberá mais notificações. Obrigado!")

            return jsonify({"status": "advogado removido e movido para advogados_excluidos"}), 200

        logger.info(f"Mensagem ignorada: '{mensagem}'")
        return jsonify({"status": "mensagem ignorada"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erro de banco: {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception("Erro inesperado no webhook")
        return jsonify({"error": str(e)}), 500
