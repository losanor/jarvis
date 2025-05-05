import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from handlers import register_handlers
from scheduler import start_scheduler
from db import criar_tabela

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

# Registrar handlers e iniciar scheduler (opcional)
register_handlers(application)
start_scheduler(application)  # Pode remover se só usar GitHub Actions

# Iniciar bot no Render via Webhook
if __name__ == "__main__":
    print("✅ Bot iniciado com Webhook no Render!")

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
