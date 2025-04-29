# handlers.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from db import adicionar_tarefa
from datetime import datetime

# Estados da conversa
AGUARDANDO_DADOS, AGUARDANDO_CATEGORIA = range(2)

# Categorias fixas
CATEGORIAS = ["Educação", "Casa", "Cartão", "Empregada", "Saúde"]

# Memória temporária do usuário
user_data_temp = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bem-vindo! Use /nova para cadastrar uma nova tarefa.")

async def nova_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Envie a tarefa no formato:\n\n"
        "`Evento, Data (dd/mm/aaaa), Recorrente (Sim/Não)`\n\n"
        "Exemplo:\n`Pagar Nubank, 10/05/2025, Sim`",
        parse_mode="Markdown"
    )
    return AGUARDANDO_DADOS

async def receber_dados_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    partes = [p.strip() for p in texto.split(",")]

    if len(partes) != 3:
        await update.message.reply_text("❌ Formato inválido. Envie novamente:")
        return AGUARDANDO_DADOS

    evento, data_str, recorrente_str = partes

    try:
        datetime.strptime(data_str, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("❌ Data inválida. Use dd/mm/aaaa.")
        return AGUARDANDO_DADOS

    if recorrente_str.lower() not in ["sim", "não"]:
        await update.message.reply_text("❌ Informe se é Recorrente: Sim ou Não.")
        return AGUARDANDO_DADOS

    user_data_temp[update.effective_user.id] = {
        "evento": evento,
        "data_vencimento": datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d"),
        "recorrente": recorrente_str.lower() == "sim"
    }

    teclado = [[KeyboardButton(c)] for c in CATEGORIAS]
    await update.message.reply_text(
        "Escolha a categoria:",
        reply_markup=ReplyKeyboardMarkup(teclado, one_time_keyboard=True, resize_keyboard=True)
    )

    return AGUARDANDO_CATEGORIA

async def receber_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categoria = update.message.text

    if categoria not in CATEGORIAS:
        await update.message.reply_text("❌ Categoria inválida. Escolha uma opção válida.")
        return AGUARDANDO_CATEGORIA

    dados = user_data_temp.get(update.effective_user.id)

    if not dados:
        await update.message.reply_text("⚠️ Algo deu errado. Comece novamente com /nova.")
        return ConversationHandler.END

    adicionar_tarefa(
        evento=dados['evento'],
        data_vencimento=dados['data_vencimento'],
        recorrente=dados['recorrente'],
        categoria=categoria
    )

    await update.message.reply_text("✅ Tarefa cadastrada com sucesso!")
    user_data_temp.pop(update.effective_user.id, None)

    return ConversationHandler.END

def register_handlers(application):
    conv_handler_nova = ConversationHandler(
        entry_points=[CommandHandler("nova", nova_tarefa)],
        states={
            AGUARDANDO_DADOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados_tarefa)],
            AGUARDANDO_CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_categoria)],
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler_nova)
