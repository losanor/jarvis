import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from handlers import register_handlers
from scheduler import start_scheduler
from db import criar_tabela
from flask import Flask, request
from threading import Thread
import asyncio

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 8443))

# Criar tabela no banco
criar_tabela()

# Criar aplicação do Telegram
application = ApplicationBuilder().token(TOKEN).build()
application.bot_data["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")
register_handlers(application)
start_scheduler(application)

# Criar app Flask
app_flask = Flask(__name__)

@app_flask.route("/force-lembrete", methods=["POST"])
def force_lembrete():
    from scheduler import enviar_lembretes
    asyncio.run(enviar_lembretes(application))
    return "Lembretes enviados!", 200

def run_flask():
    # Usa porta diferente para evitar conflito (por ex: 5000)
    PORT = int(os.environ.get("PORT", 8443))
    app_flask.run(host="0.0.0.0", port=PORT)

# Executar
if __name__ == "__main__":
    print("✅ Bot iniciado com Webhook no Render!")

    # Roda Flask em thread separada
    Thread(target=run_flask).start()

    # Roda bot com webhook na porta do Render
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
