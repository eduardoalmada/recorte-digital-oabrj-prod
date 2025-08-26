# Permite imports mais limpos
from .text_utils import normalizar_texto, criar_regex_oab, criar_regex_nome_flexivel
from .advogado_utils import buscar_mencoes_advogado

__all__ = [
    'normalizar_texto',
    'criar_regex_oab', 
    'criar_regex_nome_flexivel',
    'buscar_mencoes_advogado'
]
