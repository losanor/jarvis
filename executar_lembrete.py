# executar_lembrete.py

import os
import asyncio
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from scheduler import enviar_lembretes
from db import criar_tabela

# Carregar variáveis de ambiente
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HORARIO = os.getenv("HORARIO_EXECUCAO", "manha")  # Pode ser "manha" ou "noite"

# Criar bot mínimo
application = ApplicationBuilder().token(TOKEN).build()
application.bot_data["chat_id"] = CHAT_ID

# Criar tabela no banco (caso não exista)
criar_tabela()

# Executar lembretes com base no horário
async def main():
    print(f"🚀 Executando lembretes para o horário: {HORARIO}")
    await enviar_lembretes(application, horario=HORARIO)
    print("✅ Lembretes enviados com sucesso!")

asyncio.run(main())
