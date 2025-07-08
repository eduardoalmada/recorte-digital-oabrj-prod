from celery import shared_task

@shared_task
def tarefa_buscar_publicacoes():
    print("🔎 Buscando publicações no DataJud...")
    # Aqui vai a lógica da busca real
