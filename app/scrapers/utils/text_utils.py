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

def criar_regex_oab(numero_oab: str) -> re.Pattern:
    """
    Cria regex exclusiva para OAB/RJ, garantindo que o estado esteja sempre presente.
    É robusta para variações de pontuação e ordem, usando delimitadores suaves.
    """
    if not numero_oab:
        return re.compile("")

    normalized_input = unicodedata.normalize("NFKD", numero_oab).encode("ASCII", "ignore").decode("ASCII").upper()
    numero_limpo = re.sub(r"[^\d]", "", normalized_input)
    if not numero_limpo:
        return re.compile("")

    # Aceita até 3 separadores entre dígitos para melhor performance
    num_pattern = "".join([f"{d}[\\s\\.\\-/]{{0,3}}" for d in numero_limpo]).rstrip("[\\s\\.\\-/]{{0,3}}")

    # Padrão para OAB opcional, mas RJ obrigatório
    oab_rj_pattern = r"(?:OAB[\s\.\-/]*)?RJ"
    rj_oab_pattern = r"RJ[\s\.\-/]*(?:OAB[\s\.\-/]*)?"

    patterns = [
        # OAB/RJ + Número
        rf"{oab_rj_pattern}[\s\.\-/]*{num_pattern}",
        # Número + OAB/RJ
        rf"{num_pattern}[\s\.\-/]*{oab_rj_pattern}",
        # RJ + OAB + Número
        rf"{rj_oab_pattern}[\s\.\-/]*{num_pattern}",
        # Número + RJ + OAB
        rf"{num_pattern}[\s\.\-/]*{rj_oab_pattern}"
    ]

    final_regex = "|".join(patterns)

    # Delimitadores suaves para evitar falsos positivos em texto bagunçado
    return re.compile(rf"(?:(?<=\W)|^)(?:{final_regex})(?:(?=\W)|$)", re.IGNORECASE)

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
