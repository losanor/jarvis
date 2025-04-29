# handlers.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler
from db import adicionar_tarefa, buscar_tarefas_pendentes, marcar_como_concluido, criar_proxima_tarefa, atualizar_data_tarefa
import re
from datetime import datetime

# Estados para ConversationHandler
AGUARDANDO_DADOS, AGUARDANDO_CATEGORIA = range(2)

# Categorias fixas
CATEGORIAS = ["Educação", "Casa", "Cartão", "Empregada", "Saúde"]

# Memória temporária (para armazenar dados enquanto usuário preenche)
user_data_temp = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou seu assistente de lembretes de pagamentos.\n\n"
        "Use /nova para cadastrar uma nova tarefa.\n"
        "Use /listar para ver suas tarefas pendentes.\n"
        "Em breve mais funções!"
    )

async def nova_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Envie a tarefa no formato:\n\n"
        "`Evento, Data (dd/mm/aaaa), Recorrente (Sim/Não)`\n\n"
        "Exemplo:\n`Pagar Nubank, 10/05/2025, Sim`",
        parse_mode='Markdown'
    )
    return AGUARDANDO_DADOS

async def receber_dados_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    partes = [p.strip() for p in texto.split(",")]

    if len(partes) != 3:
        await update.message.reply_text("❌ Formato inválido. Por favor, envie no formato correto!")
        return AGUARDANDO_DADOS

    evento, data_str, recorrente_str = partes

    try:
        data = datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ Data inválida. Use o formato dd/mm/aaaa.")
        return AGUARDANDO_DADOS

    if recorrente_str.lower() not in ["sim", "não"]:
        await update.message.reply_text("❌ Informe se é Recorrente: Sim ou Não.")
        return AGUARDANDO_DADOS

    # Salva temporariamente
    user_data_temp[update.effective_user.id] = {
        "evento": evento,
        "data_vencimento": data,
        "recorrente": True if recorrente_str.lower() == "sim" else False
    }

    # Perguntar Categoria
    teclado = [[KeyboardButton(categoria)] for categoria in CATEGORIAS]
    await update.message.reply_text(
        "Escolha a categoria:",
        reply_markup=ReplyKeyboardMarkup(teclado, one_time_keyboard=True, resize_keyboard=True)
    )
    return AGUARDANDO_CATEGORIA

async def receber_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categoria = update.message.text

    if categoria not in CATEGORIAS:
        await update.message.reply_text("❌ Categoria inválida. Escolha uma das opções.")
        return AGUARDANDO_CATEGORIA

    dados = user_data_temp.get(update.effective_user.id)

    if not dados:
        await update.message.reply_text("⚠️ Algo deu errado. Por favor, tente novamente com /nova.")
        return ConversationHandler.END

    adicionar_tarefa(
        evento=dados['evento'],
        data_vencimento=dados['data_vencimento'],
        recorrente=dados['recorrente'],
        categoria=categoria
    )

    await update.message.reply_text("✅ Tarefa cadastrada com sucesso!", reply_markup=None)
    user_data_temp.pop(update.effective_user.id, None)
    return ConversationHandler.END

async def listar_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tarefas = buscar_tarefas_pendentes()

    if not tarefas:
        await update.message.reply_text("📋 Você não tem tarefas pendentes.")
        return

    texto = "📋 *Tarefas Pendentes:*\n\n"
    for tarefa in tarefas:
        id, evento, data_vencimento, categoria = tarefa
        texto += f"• {evento} | Vence em: {datetime.strptime(data_vencimento, '%Y-%m-%d').strftime('%d/%m/%Y')} | Categoria: {categoria}\n"

    await update.message.reply_text(texto, parse_mode='Markdown')

# ========= REGISTER =========

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
    application.add_handler(CommandHandler("listar", listar_tarefas))
