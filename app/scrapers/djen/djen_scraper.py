# app/scrapers/djen/djen_scraper.py
import logging
import requests
import time
from datetime import date, datetime
from typing import Dict, List
from app import db
from app.models import Advogado, AdvogadoPublicacao, DiarioOficial
import os

logger = logging.getLogger(__name__)

class DJENScraper:
    def __init__(self, client=None):  # ✅ ACEITA CLIENT EXTERNO
        if client:
            self.client = client
            self.client_externo = True  # ✅ MARCA SE CLIENT VEIO DE FORA
        else:
            from .djen_client import DJENClient
            self.client = DJENClient()
            self.client_externo = False
    
    def executar(self, data_ref: date = None) -> Dict[str, any]:
        data_ref = data_ref or date.today()
        
        resultados = {
            'data': data_ref.isoformat(),
            'total_publicacoes': 0,
            'total_mencoes': 0,
            'whatsapps_enviados': 0,
            'mencoes_detectadas': [],
            'tribunais_processados': ['DJEN'],
            'erros': []
        }
        
        try:
            logger.info("🚀 Iniciando scraping DJEN com Selenium")
            
            # 1. BUSCAR PUBLICAÇÕES
            publicacoes = self.client.buscar_publicacoes_por_data(data_ref)
            resultados['total_publicacoes'] = len(publicacoes)
            
            logger.info(f"✅ DJEN - {len(publicacoes)} publicações encontradas")
            
            if publicacoes:
                # 2. CRIAR REGISTRO NO DIÁRIO OFICIAL
                diario = DiarioOficial(
                    data_publicacao=data_ref,
                    fonte='DJEN',
                    total_publicacoes=len(publicacoes),
                    caderno='DJEN'
                )
                db.session.add(diario)
                db.session.flush()
                
                # 3. VERIFICAR ADVOGADOS MENCIONADOS
                advogados = Advogado.query.filter(Advogado.whatsapp.isnot(None)).all()
                logger.info(f"🔍 Processando {len(advogados)} advogados com WhatsApp")
                
                for publicacao in publicacoes:
                    texto_publicacao = publicacao.get('texto', '').upper()
                    
                    for advogado in advogados:
                        if (advogado.nome_completo and 
                            advogado.nome_completo.upper() in texto_publicacao and 
                            len(advogado.nome_completo) > 5):
                            
                            # 4. SALVAR MENCÃO NO BANCO
                            advogado_pub = AdvogadoPublicacao(
                                advogado_id=advogado.id,
                                diario_id=diario.id,
                                data_publicacao=data_ref,
                                qtd_mencoes=1,
                                contexto=texto_publicacao[:500],
                                titulo=publicacao.get('titulo', 'Menção DJEN'),
                                tribunal='DJEN',
                                caderno=publicacao.get('caderno', 'DJEN'),
                                link=publicacao.get('url', '')
                            )
                            db.session.add(advogado_pub)
                            resultados['total_mencoes'] += 1
                            
                            resultados['mencoes_detectadas'].append({
                                'advogado': advogado.nome_completo,
                                'whatsapp': advogado.whatsapp,
                                'publicacao': texto_publicacao[:100] + '...',
                                'oab': advogado.numero_oab
                            })
                
                # 5. SALVAR TUDO NO BANCO
                db.session.commit()
                
                # 6. ENVIAR WHATSAPP VIA UZAPI (se houver menções)
                if resultados['total_mencoes'] > 0:
                    whatsapps_enviados = self._enviar_notificacoes_uzapi(resultados['mencoes_detectadas'])
                    resultados['whatsapps_enviados'] = whatsapps_enviados
                else:
                    logger.info("📭 Nenhuma menção encontrada - WhatsApp não enviado")
                
        except Exception as e:
            db.session.rollback()
            error_msg = f"Erro no DJENScraper: {str(e)}"
            resultados['erros'].append(error_msg)
            logger.error(error_msg, exc_info=True)
        finally:
            # ✅ FECHA O CLIENT APENAS SE ELE FOI CRIADO INTERNAMENTE
            if not self.client_externo:
                self.client.close()
        
        # ✅ LOG FINAL COMPLETO
        logger.info(
            f"🎯 RESULTADO FINAL - "
            f"Publicações: {resultados['total_publicacoes']}, "
            f"Menções: {resultados['total_mencoes']}, "
            f"WhatsApps: {resultados['whatsapps_enviados']}, "
            f"Erros: {len(resultados['erros'])}"
        )
        
        return resultados
    
    def _enviar_notificacoes_uzapi(self, mencoes: List[Dict]) -> int:
        """Envia notificações via UZAPI WhatsApp com timeout e retry"""
        enviados = 0
        uzapi_url = os.getenv('UZAPI_URL')
        uzapi_token = os.getenv('UZAPI_TOKEN')
        
        if not all([uzapi_url, uzapi_token]):
            logger.warning("⚠️ Configuração UZAPI não encontrada - simulação")
            for mencao in mencoes:
                logger.info(f"📱 WhatsApp simulado para {mencao['advogado']}: {mencao['whatsapp']}")
            return len(mencoes)
        
        headers = {
            'Authorization': f'Bearer {uzapi_token}',
            'Content-Type': 'application/json'
        }
        
        for mencao in mencoes:
            try:
                mensagem = (
                    f"*Menção no DJEN encontrada!* 📢\n\n"
                    f"*Advogado:* {mencao['advogado']}\n"
                    f"*OAB:* {mencao['oab'] or 'N/A'}\n"
                    f"*Trecho:* {mencao['publicacao']}\n\n"
                    f"📅 Data: {datetime.now().strftime('%d/%m/%Y')}\n"
                    f"🔍 Fonte: Diário de Justiça Eletrônico Nacional"
                )
                
                payload = {
                    "number": mencao['whatsapp'],
                    "message": mensagem,
                    "isGroup": False
                }
                
                # ✅ TIMEOUT DE 30 SEGUNDOS
                response = requests.post(
                    f"{uzapi_url}/send-text",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ WhatsApp enviado para {mencao['advogado']}")
                    enviados += 1
                else:
                    # ✅ RETRY PARA FALHAS HTTP
                    logger.warning(f"⚠️ Retry UZAPI para {mencao['advogado']}: {response.status_code}")
                    time.sleep(2)
                    response_retry = requests.post(
                        f"{uzapi_url}/send-text",
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    if response_retry.status_code == 200:
                        logger.info(f"✅ WhatsApp enviado no retry para {mencao['advogado']}")
                        enviados += 1
                    else:
                        logger.error(f"❌ Falha UZAPI após retry: {response_retry.status_code}")
                        
            except requests.Timeout:
                logger.warning(f"⏰ Timeout UZAPI para {mencao['advogado']}")
            except requests.ConnectionError:
                logger.warning(f"🔌 ConnectionError UZAPI para {mencao['advogado']}")
            except Exception as e:
                logger.error(f"❌ Erro UZAPI para {mencao['advogado']}: {e}")
        
        return enviados
