import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder
from handlers import register_handlers
from scheduler import start_scheduler
from db import criar_tabela

# Carregar variáveis de ambiente
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")

# Criar tabela no banco (garante)
criar_tabela()

# Criar aplicação
application = ApplicationBuilder().token(TOKEN).build()

# Registrar handlers e scheduler
register_handlers(application)
start_scheduler(application)

# Iniciar bot no modo polling
if __name__ == "__main__":
    print("✅ Bot iniciado no Render!")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if __name__ == "__main__":
    print("✅ Bot iniciado com Webhook no Render!")
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=WEBHOOK_URL
    )
