# utils.py

from datetime import datetime

def validar_data(data_str):
    """Valida se a data está no formato dd/mm/aaaa"""
    try:
        datetime.strptime(data_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def formatar_data_para_db(data_str):
    """Converte dd/mm/aaaa para yyyy-mm-dd (padrão banco)"""
    data = datetime.strptime(data_str, "%d/%m/%Y")
    return data.strftime("%Y-%m-%d")

def formatar_data_para_usuario(data_str):
    """Converte yyyy-mm-dd para dd/mm/aaaa (exibir para usuário)"""
    data = datetime.strptime(data_str, "%Y-%m-%d")
    return data.strftime("%d/%m/%Y")

import unicodedata

def normalizar_texto(texto: str) -> str:
    """Remove acentos, converte para minúsculo e tira espaços extras"""
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    texto = texto.lower().strip()
    return ' '.join(texto.split())
    
