# app/scrapers/djen/djen_scraper.py
import logging
from datetime import date
from typing import Dict, List
from app import db
from app.models import Advogado

logger = logging.getLogger(__name__)

class DJENScraper:
    def __init__(self):
        from .djen_client import DJENClient
        self.client = DJENClient()
    
    def executar(self, data_ref: date = None) -> Dict[str, any]:
        data_ref = data_ref or date.today()
        
        resultados = {
            'data': data_ref.isoformat(),
            'total_publicacoes': 0,
            'total_mencoes': 0,
            'tribunais_processados': ['DJEN'],  # ✅ Adicionado DJEN como tribunal processado
            'erros': []
        }
        
        try:
            logger.info("🚀 Iniciando scraping DJEN com Selenium")
            
            # ✅ IMPLEMENTE ESTE MÉTODO NO DJENClient
            publicacoes = self.client.buscar_publicacoes_por_data(data_ref)
            resultados['total_publicacoes'] = len(publicacoes)
            
            logger.info(f"✅ DJEN - {len(publicacoes)} publicações encontradas")
            
            # Se encontrou publicações, processa menções
            if publicacoes and Advogado.query.first():  # Só processa se houver advogados
                from app.scrapers.scraper_completo_djerj import normalizar_texto
                from app.utils.advogado_utils import buscar_mencoes_advogado
                
                advogados = Advogado.query.filter_by(ativo=True).all()
                logger.info(f"🔍 Processando {len(advogados)} advogados")
                
                # ✅ LÓGICA DE MATCHING SIMPLIFICADA
                total_mencoes = 0
                for publicacao in publicacoes:
                    texto_publicacao = publicacao.get('texto', '')
                    for advogado in advogados:
                        if advogado.nome and advogado.nome.upper() in texto_publicacao.upper():
                            total_mencoes += 1
                            # ✅ AQUI VOCÊ PODE SALVAR A MENCÃO NO BANCO
                            # from app.models import Mention
                            # mention = Mention(advogado_id=advogado.id, ...)
                            # db.session.add(mention)
                
                resultados['total_mencoes'] = total_mencoes
                logger.info(f"✅ DJEN - {total_mencoes} menções encontradas")
                
            # ✅ SALVAR ALTERAÇÕES NO BANCO
            db.session.commit()
                
        except Exception as e:
            error_msg = f"Erro no DJENScraper: {str(e)}"
            resultados['erros'].append(error_msg)
            logger.error(error_msg, exc_info=True)  # ✅ Adicionado traceback completo
        finally:
            # ✅ GARANTE FECHAMENTO DO CLIENT
            self.client.close()
        
        return resultados
