# app/scrapers/utils/text_utils.py

import re
import unicodedata
from typing import Pattern

def normalizar_texto(texto: str) -> str:
    """Normalização robusta: acentos, espaços e case."""
    if not texto:
        return ""
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def criar_regex_oab(numero_oab: str) -> Pattern:
    """
    Cria regex exclusiva para OAB/RJ que captura TODAS as variações:
    - OAB/RJ-123456, OAB/RJ 123456, OAB/RJ123456
    - OAB/RJ nº 123456, OAB/RJ n° 123456
    - OAB/RJ sob o nº 123456, OAB/RJ sob o n° 123456
    - E todas as combinações com pontuação variada
    """
    if not numero_oab:
        return re.compile("")

    # Extrai APENAS os números para busca flexível
    numeros_limpos = re.sub(r'[^\d]', '', numero_oab)
    if not numeros_limpos:
        return re.compile("")

    # Padrões que capturam TODAS as variações possíveis
    patterns = [
        # Formato padrão: OAB/RJ-123456, OAB/RJ 123456, OAB/RJ123456
        r'OAB[\/\\]?RJ[\/\\\-\.\s]*' + numeros_limpos,
        
        # Formato com "nº" ou "n°": OAB/RJ nº 123456, OAB/RJ n° 123456
        r'OAB[\/\\]?RJ[\/\\\-\.\s]*n[º°]?[\/\\\-\.\s]*' + numeros_limpos,
        
        # Formato com "sob o nº": OAB/RJ sob o nº 123456, OAB/RJ sob o n° 123456
        r'OAB[\/\\]?RJ[\/\\\-\.\s]*sob\s+o\s+n[º°]?[\/\\\-\.\s]*' + numeros_limpos,
        
        # Formato com ponto nos números: 12.345, 98.885
        r'OAB[\/\\]?RJ[\/\\\-\.\s]*' + numeros_limpos[:2] + r'[\.]?' + numeros_limpos[2:],
        
        # Formato apenas números (fallback): 123456
        r'[\/\\\-\.\s]' + numeros_limpos + r'[\/\\\-\.\s]',
        
        # Formato com "sob o nº" e ponto: OAB/RJ sob o nº 12.345
        r'OAB[\/\\]?RJ[\/\\\-\.\s]*sob\s+o\s+n[º°]?[\/\\\-\.\s]*' + numeros_limpos[:2] + r'[\.]?' + numeros_limpos[2:]
    ]
    
    # Combina todos os padrões com delimitadores suaves
    final_regex = '|'.join(patterns)
    return re.compile(rf'(?:(?<=\W)|^)(?:{final_regex})(?:(?=\W)|$)', re.IGNORECASE)

def criar_regex_nome_flexivel(nome_completo: str) -> Pattern:
    """Cria regex que detecta nomes mesmo quando colados com texto anterior."""
    nome_norm = normalizar_texto(nome_completo)
    partes = nome_norm.split()
    
    regex_partes = []
    for i, parte in enumerate(partes):
        if i == 0:
            regex_partes.append(r'(\w*' + re.escape(parte) + r')')
        else:
            regex_partes.append(r'[\s]?' + re.escape(parte))
    
    return re.compile(r'\s+'.join(regex_partes), re.IGNORECASE)
