# handlers.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
from scheduler import scheduler, enviar_lembrete_19h
from utils import formatar_data_para_db, validar_data
from db import marcar_como_concluido, criar_proxima_tarefa, atualizar_data_tarefa, adicionar_tarefa, buscar_tarefas_pendentes


# Estados da conversa
AGUARDANDO_DADOS, AGUARDANDO_CATEGORIA = range(2)

# Categorias fixas
CATEGORIAS = ["Educação", "Casa", "Cartão", "Empregada", "Saúde"]

# Memória temporária do usuário
user_data_temp = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou a AIA.\n\n"
        "Use /nova - cadastrar pagamento.\n"
        "Use /listar - pagamentos pendentes.\n"
        "Use /editar - editar pagamento.\n"
    )

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
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d{2}/\d{2}/\d{4}$"), receber_nova_data))


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("fazer_"):
        tarefa_id = int(data.split("_")[1])
        marcar_como_concluido(tarefa_id)
        criar_proxima_tarefa(tarefa_id)
        await query.edit_message_text("✅ Tarefa concluída com sucesso!")

    elif data.startswith("lembrar_19h_"):
        tarefa_id = int(data.split("_")[2])
        # Agendar o lembrete extra às 19h do mesmo dia
        hoje_19h = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        scheduler.add_job(lambda: enviar_lembrete_19h(context.application, tarefa_id),
                              'date', run_date=hoje_19h)
        await query.edit_message_text("🔁 Lembrete reprogramado para hoje às 19h!")

    elif data.startswith("reagendar_"):
        tarefa_id = int(data.split("_")[1])

        teclado = [
            [
                InlineKeyboardButton("Hoje à noite (19h)", callback_data=f"reagendar_hoje_{tarefa_id}"),
                InlineKeyboardButton("Amanhã (9h)", callback_data=f"reagendar_amanha_{tarefa_id}")
            ],
            [InlineKeyboardButton("Escolher outra data", callback_data=f"reagendar_escolher_{tarefa_id}")]
        ]
        await query.edit_message_text(
            "🔁 Escolha quando deseja reagendar:",
            reply_markup=InlineKeyboardMarkup(teclado)
        )

    elif data.startswith("reagendar_hoje_"):
        tarefa_id = int(data.split("_")[2])
        hoje_19h = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        nova_data = hoje_19h.strftime("%Y-%m-%d")
        atualizar_data_tarefa(tarefa_id, nova_data)
        await query.edit_message_text("✅ Tarefa reagendada para hoje à noite (19h)!")

    elif data.startswith("reagendar_amanha_"):
        tarefa_id = int(data.split("_")[2])
        amanha = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        nova_data = amanha.strftime("%Y-%m-%d")
        atualizar_data_tarefa(tarefa_id, nova_data)
        await query.edit_message_text("✅ Tarefa reagendada para amanhã às 9h!")

    elif data.startswith("reagendar_escolher_"):
        tarefa_id = int(data.split("_")[2])
        context.user_data["reagendar_tarefa_id"] = tarefa_id
        await query.edit_message_text("✏️ Digite a nova data no formato dd/mm/aaaa:")

async def receber_nova_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tarefa_id = context.user_data.get("reagendar_tarefa_id")
    data_digitada = update.message.text

    if not validar_data(data_digitada):
        await update.message.reply_text("❌ Data inválida. Use o formato dd/mm/aaaa.")
        return

    nova_data = formatar_data_para_db(data_digitada)
    atualizar_data_tarefa(tarefa_id, nova_data)
    await update.message.reply_text("✅ Tarefa reagendada com sucesso!")
    context.user_data.pop("reagendar_tarefa_id", None)

