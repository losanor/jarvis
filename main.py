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
    application.run_polling()
