# UTILITIES ESPECÍFICAS PARA BUSCA DE ADVOGADOS
import re
from typing import List
from app.models import Advogado
from .text_utils import normalizar_texto, criar_regex_oab, criar_regex_nome_flexivel

def buscar_mencoes_advogado(texto_norm: str, advogado: Advogado) -> List[re.Match]:
    """Busca todas as menções válidas do advogado no texto normalizado."""
    resultados = []
    
    nome_pattern = criar_regex_nome_flexivel(advogado.nome_completo)
    
    if advogado.numero_oab:
        oab_pattern = criar_regex_oab(advogado.numero_oab)
        padrao_completo = f"({nome_pattern})" + r".{0,80}?" + f"({oab_pattern})"
        
        for match in re.finditer(padrao_completo, texto_norm, re.IGNORECASE):
            resultados.append(match)
    else:
        for match in re.finditer(nome_pattern, texto_norm, re.IGNORECASE):
            resultados.append(match)
    
    return resultados
