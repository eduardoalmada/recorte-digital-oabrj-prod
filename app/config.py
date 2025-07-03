import os

class Config:
    REDIS_BROKER_URL = os.getenv("REDIS_BROKER_URL")
    DATAJUD_API_URL = "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search"
    DATAJUD_API_KEY = os.getenv("DATAJUD_API_KEY")
