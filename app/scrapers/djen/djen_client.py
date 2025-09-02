import requests
import logging
from datetime import date
from typing import List, Dict
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class DJENClient:
    BASE_URL = "https://comunica.pje.jus.br"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        })
    
    def buscar_publicacoes_por_data(self, data: date) -> List[Dict]:
        """Busca publicações no DJEN usando o endpoint real"""
        try:
            url = f"{self.BASE_URL}/consulta"
            params = {
                'dataDisponibilizacaoInicio': data.strftime('%Y-%m-%d'),
                'dataDisponibilizacaoFim': data.strftime('%Y-%m-%d')
            }
            
            logger.info(f"🔍 Buscando publicações DJEN: {url}?{params}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Verifica se a resposta é HTML (sucesso) ou JSON (erro)
            if 'application/json' in response.headers.get('content-type', ''):
                logger.error("Resposta em JSON - possível erro de autenticação")
                return []
            
            return self._parse_resultados(response.text, data)
            
        except Exception as e:
            logger.error(f"Erro ao buscar publicações DJEN: {e}")
            return []
    
    def _parse_resultados(self, html: str, data: date) -> List[Dict]:
        """Analisa o HTML dos resultados da busca"""
        soup = BeautifulSoup(html, 'html.parser')
        resultados = []
        
        # Procura por tabelas ou listas de resultados
        tabelas = soup.find_all('table')
        logger.info(f"Encontradas {len(tabelas)} tabelas na página")
        
        # Padrões comuns para identificar resultados
        padroes_tabela = [
            {'class': 'resultado'},
            {'class': 'publicacao'},
            {'class': 'consulta'},
            {'id': 'resultados'},
            {'role': 'grid'}
        ]
        
        for tabela in tabelas:
            try:
                # Verifica se esta tabela parece conter resultados
                if self._e_tabela_de_resultados(tabela):
                    linhas = tabela.find_all('tr')[1:]  # Pula cabeçalho
                    
                    for linha in linhas:
                        publicacao = self._extrair_publicacao(linha, data)
                        if publicacao:
                            resultados.append(publicacao)
                            
                    logger.info(f"Extraídas {len(resultados)} publicações da tabela")
                    break  # Assume que a primeira tabela de resultados é a correta
                    
            except Exception as e:
                logger.warning(f"Erro ao processar tabela: {e}")
                continue
        
        # Fallback: procura por links de publicações em qualquer lugar da página
        if not resultados:
            resultados = self._fallback_search(soup, data)
        
        return resultados
    
    def _e_tabela_de_resultados(self, tabela) -> bool:
        """Verifica se a tabela parece conter resultados de publicações"""
        texto_tabela = tabela.get_text().lower()
        indicadores = ['publicacao', 'comunicacao', 'diario', 'processo', 'advogado']
        return any(ind in texto_tabela for ind in indicadores)
    
    def _extrair_publicacao(self, linha, data: date) -> Dict:
        """Extrai dados de uma publicação individual da linha da tabela"""
        try:
            celulas = linha.find_all('td')
            if len(celulas) < 2:
                return None
            
            # Tenta extrair link e informações básicas
            link_tag = celulas[0].find('a')
            if not link_tag:
                return None
            
            publicacao = {
                'id': self._extrair_id(link_tag.get('href', '')),
                'titulo': link_tag.get_text(strip=True),
                'tribunal': celulas[1].get_text(strip=True) if len(celulas) > 1 else '',
                'orgao_julgador': celulas[2].get_text(strip=True) if len(celulas) > 2 else '',
                'data_publicacao': data,
                'url': self._construir_url(link_tag.get('href', '')),
                'pagina': None
            }
            
            return publicacao
            
        except Exception as e:
            logger.warning(f"Erro ao extrair publicação: {e}")
            return None
    
    def _fallback_search(self, soup, data: date) -> List[Dict]:
        """Busca fallback por publicações na página"""
        resultados = []
        
        # Procura por links que parecem ser de publicações
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            texto = link.get_text(strip=True)
            
            if self._parece_publicacao(href, texto):
                publicacao = {
                    'id': self._extrair_id(href),
                    'titulo': texto,
                    'tribunal': '',
                    'orgao_julgador': '',
                    'data_publicacao': data,
                    'url': self._construir_url(href),
                    'pagina': None
                }
                resultados.append(publicacao)
        
        return resultados
    
    def _parece_publicacao(self, href: str, texto: str) -> bool:
        """Verifica se o link parece ser uma publicação"""
        if not texto or len(texto) < 10:
            return False
        
        padroes_href = ['/publicacao/', '/consulta/', 'publicacaoId=', 'id=']
        padroes_texto = ['publicacao', 'comunicacao', 'processo', 'intimacao']
        
        return (any(p in href.lower() for p in padroes_href) or
                any(p in texto.lower() for p in padroes_texto))
    
    def _extrair_id(self, href: str) -> str:
        """Extrai ID da publicação do href"""
        padroes_id = [
            r'publicacaoId=(\d+)',
            r'id=(\d+)',
            r'/publicacao/(\d+)',
            r'/detalhe/(\d+)'
        ]
        
        for padrao in padroes_id:
            match = re.search(padrao, href)
            if match:
                return match.group(1)
        
        return href  # Fallback: retorna o próprio href
    
    def _construir_url(self, href: str) -> str:
        """Constrói URL completa a partir de href relativo"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return f"{self.BASE_URL}{href}"
        else:
            return f"{self.BASE_URL}/{href}"
