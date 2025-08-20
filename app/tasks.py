# app/tasks.py
from celery import shared_task
import logging
from app.scrapers import scraper_djerj_selenium  # importa o scraper robusto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

@shared_task(name="app.tasks.tarefa_buscar_publicacoes")
def tarefa_buscar_publicacoes():
    """
    Task principal que será disparada pelo Celery Beat todos os dias às 15h.
    Chama o scraper robusto do DJERJ para o DO do dia atual,
    salva no banco, busca menções de advogados e envia WhatsApp.
    """
    try:
        logging.info("Task iniciar: buscar publicações do DO do dia")
        scraper_djerj_selenium.main()  # chama o scraper robusto
        logging.info("Task concluída: publicações do DO processadas")
    except Exception as e:
        logging.error(f"Erro na task tarefa_buscar_publicacoes: {e}")
        # opcional: aqui você pode integrar alertas via Slack/WhatsApp/email
