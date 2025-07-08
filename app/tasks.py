from celery import shared_task

@shared_task
def tarefa_buscar_publicacoes():
    print("🔎 Iniciando busca de publicações no DataJud...")
    # Lógica real da busca vai aqui
