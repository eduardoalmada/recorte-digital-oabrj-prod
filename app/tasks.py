# app/tasks.py
from celery import current_app as celery
from app import create_app
import logging
from functools import lru_cache
import requests
import os
from datetime import datetime, date, timedelta
import psutil
import traceback

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_flask_app():
    app = create_app()
    app.app_context().push()
    return app

# ✅ TASK PRINCIPAL MELHORADA COM LOGS DETALHADOS
@celery.task(
    name='app.tasks.tarefa_buscar_publicacoes',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300
)
def tarefa_buscar_publicacoes(self):
    """Task principal com proteção contra sobrecarga e logs detalhados"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            logger.info("🚀 Iniciando tarefa de busca de publicações...")
            
            # ✅ MONITORAR MEMÓRIA ANTES DE CRIAR DRIVER
            memoria = psutil.virtual_memory()
            if memoria.percent > 80:
                logger.warning(f"⚠️ Memória alta ({memoria.percent}%), adiando task...")
                raise self.retry(countdown=300)
            
            from app.scrapers.djen.djen_client import DJENClient
            client = DJENClient()
            
            from app.scrapers.djen.djen_scraper import DJENScraper
            scraper = DJENScraper(client=client)
            
            resultado_djen = scraper.executar()
            
            # ✅ LOG DETALHADO PARA MONITORAMENTO
            logger.info(f"✅ DJEN - {resultado_djen['total_publicacoes']} publicações encontradas")
            
            # ✅ VERIFICAR SE REALMENTE CAPTUROU PUBLICAÇÕES
            from app.models import Publicacao
            publicacoes_hoje = Publicacao.query.filter(
                Publicacao.data_criacao >= date.today()
            ).count()
            
            resultado = {
                'status': 'success', 
                'message': 'Tarefas concluídas',
                'resultado_djen': resultado_djen,
                'publicacoes_hoje': publicacoes_hoje,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"📊 Resultado final: {publicacoes_hoje} publicações capturadas hoje")
            
            return resultado
            
    except MemoryError as e:
        logger.warning(f"🛑 Memória insuficiente: {e}, retry em 5min")
        raise self.retry(exc=e, countdown=300)
    except Exception as e:
        logger.error(f"❌ Erro na tarefa de scraping: {e}")
        logger.error(f"📋 Stack trace: {traceback.format_exc()}")
        raise self.retry(exc=e, countdown=300)
    finally:
        if 'client' in locals():
            try:
                client.close()
                logger.info("✅ ChromeDriver fechado com sucesso")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao fechar client: {e}")

# ✅ TASK: Enviar relatório diário via UZAPI
@celery.task(name='app.tasks.enviar_relatorio_diario')
def enviar_relatorio_diario():
    """Enviar relatório diário via UZAPI WhatsApp"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            from app.models import Advogado, Publicacao
            
            # Estatísticas
            total_advogados = Advogado.query.count()
            total_publicacoes = Publicacao.query.count()
            publicacoes_hoje = Publicacao.query.filter(
                Publicacao.data_criacao >= date.today()
            ).count()
            
            # Mensagem formatada
            mensagem = f"""📊 *RELATÓRIO DIÁRIO - RECORTE DIGITAL*

• Advogados monitorados: {total_advogados}
• Publicações totais: {total_publicacoes}
• Novas publicações hoje: {publicacoes_hoje}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
            """
            
            # Enviar para administradores
            administradores = os.getenv('ADMIN_WHATSAPP_NUMBERS', '').split(',')
            
            for numero in administradores:
                if numero.strip():
                    enviar_whatsapp_uzapi.delay(numero.strip(), mensagem)
                    
            logger.info("✅ Relatório diário enviado com sucesso")
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar relatório diário: {e}")
        raise

# ✅ TASK: Verificar novas publicações
@celery.task(name='app.tasks.verificar_novas_publicacoes')
def verificar_novas_publicacoes():
    """Verificar e notificar novas publicações"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            from app.models import Publicacao
            from app import db
            
            # Verificar publicações das últimas 2 horas
            duas_horas_atras = datetime.now() - timedelta(hours=2)
            
            novas_publicacoes = Publicacao.query.filter(
                Publicacao.data_criacao >= duas_horas_atras,
                Publicacao.notificada == False
            ).all()
            
            if novas_publicacoes:
                for publicacao in novas_publicacoes:
                    mensagem = f"📢 Nova publicação para {publicacao.advogado.nome}:\n{publicacao.titulo}"
                    
                    # Enviar notificação
                    enviar_whatsapp_uzapi.delay(
                        publicacao.advogado.whatsapp, 
                        mensagem
                    )
                    
                    # Marcar como notificada
                    publicacao.notificada = True
                
                db.session.commit()
                logger.info(f"✅ {len(novas_publicacoes)} novas publicações notificadas")
            
    except Exception as e:
        logger.error(f"❌ Erro ao verificar publicações: {e}")
        raise

# ✅ TASK: Enviar WhatsApp via UZAPI
@celery.task(
    name='app.tasks.enviar_whatsapp_uzapi',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def enviar_whatsapp_uzapi(self, numero, mensagem, media_url=None):
    """Enviar mensagem via UZAPI WhatsApp"""
    try:
        uzapi_url = os.getenv('UZAPI_BASE_URL')
        api_key = os.getenv('UZAPI_API_KEY')
        instance_id = os.getenv('UZAPI_INSTANCE_ID')
        
        if not all([uzapi_url, api_key, instance_id]):
            raise ValueError("Configurações UZAPI incompletas")
        
        url = f"{uzapi_url}/v1/messages"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "instance_id": instance_id,
            "to": numero,
            "type": "text",
            "text": {
                "body": mensagem
            }
        }
        
        if media_url:
            payload["type"] = "media"
            payload["media"] = {
                "url": media_url,
                "caption": mensagem
            }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"✅ WhatsApp enviado via UZAPI para {numero}")
        return response.json()
        
    except Exception as e:
        logger.error(f"❌ Falha ao enviar WhatsApp para {numero}: {e}")
        self.retry(exc=e)

# ✅ TASK: Fallback para caso o scraping das 18h falhe
@celery.task(name='app.tasks.tentar_novamente_se_falhar')
def tentar_novamente_se_falhar():
    """Tenta novamente se o scraping das 18h falhou ou não encontrou publicações"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            from app.models import Publicacao
            
            # Verificar se não há publicações de hoje
            publicacoes_hoje = Publicacao.query.filter(
                Publicacao.data_criacao >= date.today()
            ).count()
            
            if publicacoes_hoje == 0:
                logger.warning("⚠️ Nenhuma publicação encontrada hoje, executando fallback às 21h...")
                
                # Executar scraping novamente
                resultado = tarefa_buscar_publicacoes.apply()
                
                logger.info(f"✅ Fallback executado: {resultado.get('message', 'Sucesso')}")
                return {
                    'status': 'fallback_executed',
                    'publicacoes_encontradas': publicacoes_hoje,
                    'resultado_fallback': resultado.result
                }
            else:
                logger.info(f"✅ Já existem {publicacoes_hoje} publicações hoje, fallback não necessário")
                return {
                    'status': 'fallback_not_needed', 
                    'publicacoes_encontradas': publicacoes_hoje
                }
            
    except Exception as e:
        logger.error(f"❌ Erro no fallback: {e}")
        raise

# ✅ TASK: Verificar status do sistema
@celery.task(name='app.tasks.verificar_status_sistema')
def verificar_status_sistema():
    """Verifica o status geral do sistema"""
    app = get_flask_app()
    
    try:
        with app.app_context():
            from app.models import Advogado, Publicacao
            
            # Estatísticas do sistema
            total_advogados = Advogado.query.count()
            total_publicacoes = Publicacao.query.count()
            
            # Publicações das últimas 24h
            um_dia_atras = datetime.now() - timedelta(hours=24)
            publicacoes_24h = Publicacao.query.filter(
                Publicacao.data_criacao >= um_dia_atras
            ).count()
            
            # Publicações de hoje
            publicacoes_hoje = Publicacao.query.filter(
                Publicacao.data_criacao >= date.today()
            ).count()
            
            status = {
                'timestamp': datetime.now().isoformat(),
                'total_advogados': total_advogados,
                'total_publicacoes': total_publicacoes,
                'publicacoes_24h': publicacoes_24h,
                'publicacoes_hoje': publicacoes_hoje,
                'status': 'healthy' if publicacoes_hoje > 0 else 'warning'
            }
            
            logger.info(f"📈 Status do sistema: {status}")
            return status
            
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {e}")
        return {'status': 'error', 'message': str(e)}

# ✅ Health check para workers
@celery.task(name='app.tasks.health_check')
def health_check():
    """Task simples para verificar se worker está vivo"""
    return {'status': 'healthy', 'service': 'celery_worker'}