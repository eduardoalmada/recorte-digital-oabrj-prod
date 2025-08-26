# UTILITIES PARA PROCESSAMENTO DE TEXTO
import re
import unicodedata
from typing import List

def normalizar_texto(texto: str) -> str:
    """Normalização robusta: acentos, espaços e case."""
    if not texto:
        return ""
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def criar_regex_oab(numero_oab: str) -> str:
    """Cria regex flexível para todas as variações de OAB."""
    if not numero_oab:
        return ""
    oab_clean = re.sub(r'[^\w\s]', ' ', numero_oab.upper())
    oab_clean = re.sub(r'\s+', ' ', oab_clean).strip()
    partes = oab_clean.split()
    
    regex_partes = []
    for parte in partes:
        if parte.isdigit() and len(parte) > 2:
            regex_partes.append(r'[\s\-\.]*' + re.escape(parte) + r'[\s\-\.]*')
        else:
            regex_partes.append(r'[\s\/\-\.]*' + re.escape(parte) + r'[\s\/\-\.]*')
    
    return ''.join(regex_partes)

def criar_regex_nome_flexivel(nome_completo: str) -> str:
    """Cria regex que detecta nomes mesmo quando colados com texto anterior."""
    nome_norm = normalizar_texto(nome_completo)
    partes = nome_norm.split()
    
    regex_partes = []
    for i, parte in enumerate(partes):
        if i == 0:
            regex_partes.append(r'(\w*' + re.escape(parte) + r')')
        else:
            regex_partes.append(r'[\s]?' + re.escape(parte))
    
    return r'\s+'.join(regex_partes)
