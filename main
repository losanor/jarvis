# main.py

import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from handlers import register_handlers
from scheduler import start_scheduler

#Carregar variaveis de ambiente
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN não encontrado no ambiente!")

async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Registra os handlers de comandos e mensagens
    register_handlers(application)

    # Inicia o agendador de tarefas (lembretes, etc)
    start_scheduler(application)

    print("✅ Bot iniciado!")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
