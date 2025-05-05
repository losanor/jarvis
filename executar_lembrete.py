# executar_lembrete.py
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from scheduler import enviar_lembretes
from db import criar_tabela

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Cria bot mínimo
application = ApplicationBuilder().token(TOKEN).build()
application.bot_data["chat_id"] = CHAT_ID

# Cria tabela caso não exista
criar_tabela()

# Executa lembretes
import asyncio
asyncio.run(enviar_lembretes(application))
