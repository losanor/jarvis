# handlers.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime, timedelta
from scheduler import scheduler, enviar_lembrete_19h
from utils import formatar_data_para_db, validar_data, normalizar_texto
from db import marcar_como_concluido, criar_proxima_tarefa, atualizar_data_tarefa, adicionar_tarefa, buscar_tarefas_pendentes, atualizar_tarefa, deletar_tarefa


# Estados da conversa
AGUARDANDO_DADOS, AGUARDANDO_CATEGORIA, CONFIRMAR_NOVO_CADASTRO, AGUARDANDO_NOVA_DATA, AGUARDANDO_NOVA_RECORRENCIA, AGUARDANDO_NOVA_DESCRICAO = range(6)

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

    # 🔵 >>>>>> Aqui entra o novo código <<<<<< 🔵
    evento_normalizado = normalizar_texto(evento)

    tarefas_existentes = buscar_tarefas_pendentes()
    for tarefa in tarefas_existentes:
        _, evento_existente, _, _ = tarefa
        if normalizar_texto(evento_existente) == evento_normalizado:
            await update.message.reply_text(
                f"⚠️ Já existe uma tarefa parecida: *{evento_existente}*.\nDeseja continuar mesmo assim?",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("✅ Sim"), KeyboardButton("❌ Não")]],
                    one_time_keyboard=True,
                    resize_keyboard=True
                )
            )

            # Guardar dados temporários pra usar depois
            context.user_data["dados_tarefa_pendente"] = {
                "evento": evento,
                "data_vencimento": datetime.strptime(data_str, "%d/%m/%Y").strftime("%Y-%m-%d"),
                "recorrente": recorrente_str.lower() == "sim"
            }
            return CONFIRMAR_NOVO_CADASTRO  # vai para fluxo de confirmação

    # 🔵 >>>>>> Fim da verificação de duplicidade 🔵

    # Se não encontrar duplicado, seguir normal:
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

    await update.message.reply_text(
        "✅ Tarefa cadastrada com sucesso!\n\nDeseja cadastrar outra tarefa?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("✅ Sim"), KeyboardButton("❌ Não")]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    user_data_temp.pop(update.effective_user.id, None)
    return CONFIRMAR_NOVO_CADASTRO

async def listar_tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tarefas = buscar_tarefas_pendentes()

    if not tarefas:
        await update.message.reply_text("📋 Você não tem tarefas pendentes.")
        return

    texto = "📋 *Tarefas Pendentes:*\n\n"
    for tarefa in tarefas:
        id, evento, data_vencimento, categoria = tarefa
        texto += f"• {evento} | Vence em: {data_vencimento.strftime('%d/%m/%Y')} | Categoria: {categoria}\n"


    await update.message.reply_text(texto, parse_mode='Markdown')

def register_handlers(application):
    # Handler para cadastro de novas tarefas
    conv_handler_nova = ConversationHandler(
        entry_points=[CommandHandler("nova", nova_tarefa)],
        states={
            AGUARDANDO_DADOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados_tarefa)],
            AGUARDANDO_CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_categoria)],
            CONFIRMAR_NOVO_CADASTRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_novo_cadastro)],
        },
        fallbacks=[CommandHandler("nova", nova_tarefa)],
        allow_reentry=True
    )

    # Handler para edição de tarefas
    conv_handler_edicao = ConversationHandler(
        entry_points=[
            CommandHandler("editar", editar)],
            CallbackQueryHandler(callback_handler)
        ],
        states={
            AGUARDANDO_NOVA_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nova_data_edicao)],
            AGUARDANDO_NOVA_RECORRENCIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nova_recorrencia)],
            AGUARDANDO_NOVA_DESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nova_descricao)],
        },
        fallbacks=[],
        allow_reentry=True
    )

    # Registro de todos os handlers na aplicação
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler_nova)
    application.add_handler(conv_handler_edicao)
    application.add_handler(CommandHandler("listar", listar_tarefas))

async def tarefa_enviar_lembrete(application, tarefa_id):
    await enviar_lembrete_19h(application, tarefa_id)

#funcoes detalhadas
async def handle_fazer(query, tarefa_id, context):
    marcar_como_concluido(tarefa_id)
    criar_proxima_tarefa(tarefa_id)
    await query.edit_message_text("✅ Tarefa concluída com sucesso!")

async def handle_lembrar_19h(query, tarefa_id, context):
    hoje_19h = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
    scheduler.add_job(tarefa_enviar_lembrete, 'date', run_date=hoje_19h, args=[context.application, tarefa_id])
    await query.edit_message_text("🔁 Lembrete reprogramado para hoje às 19h!")

async def handle_reagendar(query, tarefa_id):
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

async def handle_reagendar_hoje(query, tarefa_id):
    hoje_19h = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
    nova_data = hoje_19h.strftime("%Y-%m-%d")
    atualizar_data_tarefa(tarefa_id, nova_data)
    await query.edit_message_text("✅ Tarefa reagendada para hoje à noite (19h)!")


#Edicao das tarefas
async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tarefas = buscar_tarefas_pendentes()
    if not tarefas:
        await update.message.reply_text("📭 Você não tem pagamentos para editar.")
        return

    teclado = []
    for tarefa in tarefas:
        id, evento, data_vencimento, categoria = tarefa
        texto_botao = f"{evento} ({data_vencimento.strftime('%d/%m/%Y')})"
        teclado.append([InlineKeyboardButton(texto_botao, callback_data=f"editar_{id}")])

    await update.message.reply_text(
        "✏️ Qual pagamento você deseja editar?",
        reply_markup=InlineKeyboardMarkup(teclado)
    )
    return ConversationHandler.END

async def handle_reagendar_amanha(query, tarefa_id):
    amanha = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    nova_data = amanha.strftime("%Y-%m-%d")
    atualizar_data_tarefa(tarefa_id, nova_data)
    await query.edit_message_text("✅ Tarefa reagendada para amanhã às 9h!")

async def handle_reagendar_escolher(query, tarefa_id, context):
    context.user_data["reagendar_tarefa_id"] = tarefa_id
    await query.edit_message_text("✏️ Digite a nova data no formato dd/mm/aaaa:")

async def confirmar_novo_cadastro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = update.message.text.lower()

    if "sim" in resposta:
        if "dados_tarefa_pendente" in context.user_data:
            dados = context.user_data.pop("dados_tarefa_pendente")
            user_data_temp[update.effective_user.id] = dados

            teclado = [[KeyboardButton(c)] for c in CATEGORIAS]
            await update.message.reply_text(
                "Escolha a categoria para a nova tarefa:",
                reply_markup=ReplyKeyboardMarkup(teclado, one_time_keyboard=True, resize_keyboard=True)
            )
            return AGUARDANDO_CATEGORIA
        else:
            await nova_tarefa(update, context)  # Reinicia cadastro normal
            return AGUARDANDO_DADOS
    else:
        await update.message.reply_text("✅ Missão cumprida! Volte quando quiser.")
        return ConversationHandler.END

async def receber_nova_data_edicao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nova_data = update.message.text.strip()
    if not validar_data(nova_data):
        await update.message.reply_text("❌ Data inválida. Use o formato dd/mm/aaaa:")
        return AGUARDANDO_NOVA_DATA

    tarefa_id = context.user_data.get("editar_tarefa_id")
    atualizar_data_tarefa(tarefa_id, formatar_data_para_db(nova_data))
    await update.message.reply_text("✅ Data atualizada com sucesso!")
    return ConversationHandler.END


async def receber_nova_recorrencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nova = update.message.text.strip().lower()
    if nova not in ["sim", "não"]:
        await update.message.reply_text("❌ Valor inválido. Responda com Sim ou Não:")
        return AGUARDANDO_NOVA_RECORRENCIA

    tarefa_id = context.user_data.get("editar_tarefa_id")
    atualizar_tarefa(tarefa_id, campo="recorrente", valor=1 if nova == "sim" else 0)
    await update.message.reply_text("✅ Recorrência atualizada com sucesso!")
    return ConversationHandler.END


async def receber_nova_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nova_desc = update.message.text.strip()
    if not nova_desc:
        await update.message.reply_text("❌ A descrição não pode estar vazia:")
        return AGUARDANDO_NOVA_DESCRICAO

    tarefa_id = context.user_data.get("editar_tarefa_id")
    atualizar_tarefa(tarefa_id, campo="evento", valor=nova_desc)
    await update.message.reply_text("✅ Descrição atualizada com sucesso!")
    return ConversationHandler.END
    
#callback
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- Ações relacionadas à tarefa concluída ou reagendada ---
    if data.startswith("fazer_"):
        tarefa_id = int(data.split("_")[1])
        await handle_fazer(query, tarefa_id, context)

    elif data.startswith("lembrar_19h_"):
        tarefa_id = int(data.split("_")[2])
        await handle_lembrar_19h(query, tarefa_id, context)

    elif data.startswith("reagendar_"):
        tarefa_id = int(data.split("_")[1])
        await handle_reagendar(query, tarefa_id)

    elif data.startswith("reagendar_hoje_"):
        tarefa_id = int(data.split("_")[2])
        await handle_reagendar_hoje(query, tarefa_id)

    elif data.startswith("reagendar_amanha_"):
        tarefa_id = int(data.split("_")[2])
        await handle_reagendar_amanha(query, tarefa_id)

    elif data.startswith("reagendar_escolher_"):
        tarefa_id = int(data.split("_")[2])
        await handle_reagendar_escolher(query, tarefa_id, context)

    # --- Ações relacionadas à edição da tarefa ---
    elif data.startswith("editar_"):
        comando = data.split("_")[1]
        
        if comando.isdigit():
            # Quando for editar_<ID>, ou seja, selecionar a tarefa
            tarefa_id = int(comando)
            context.user_data["editar_tarefa_id"] = tarefa_id
    
            botoes = [
                [InlineKeyboardButton("🗓 Alterar Data", callback_data="editar_data")],
                [InlineKeyboardButton("✍️ Alterar Descrição", callback_data="editar_descricao")],
                [InlineKeyboardButton("🗑 Excluir Tarefa", callback_data="excluir_tarefa")]
            ]
            await query.edit_message_text("O que você deseja editar?", reply_markup=InlineKeyboardMarkup(botoes))
    
        elif comando == "data":
            await query.edit_message_text("Digite a nova data no formato dd/mm/aaaa:")
            return AGUARDANDO_NOVA_DATA
    
        elif comando == "recorrencia":
            await query.edit_message_text("♻️ A tarefa será recorrente? Responda: Sim ou Não.")
            return AGUARDANDO_NOVA_RECORRENCIA
    
        elif comando == "descricao":
            await query.edit_message_text("Digite a nova descrição para a tarefa:")
            return AGUARDANDO_NOVA_DESCRICAO
    
    # --- Exclusão com confirmação ---
    elif data == "excluir_tarefa":
        tarefa_id = context.user_data.get("editar_tarefa_id")
        if not tarefa_id:
            await query.edit_message_text("⚠️ Tarefa não encontrada.")
            return

        context.user_data["confirmar_exclusao_id"] = tarefa_id

        botoes = [
            [
                InlineKeyboardButton("✅ Sim", callback_data="confirmar_exclusao_sim"),
                InlineKeyboardButton("❌ Não", callback_data="confirmar_exclusao_nao")
            ]
        ]
        await query.edit_message_text("⚠️ Tem certeza que deseja excluir a tarefa?", reply_markup=InlineKeyboardMarkup(botoes))

    elif data == "confirmar_exclusao_sim":
        tarefa_id = context.user_data.pop("confirmar_exclusao_id", None)
        if tarefa_id:
            deletar_tarefa(tarefa_id)
            await query.edit_message_text("🗑 Tarefa excluída com sucesso!")
        else:
            await query.edit_message_text("❌ Não foi possível encontrar a tarefa para excluir.")

    elif data == "confirmar_exclusao_nao":
        context.user_data.pop("confirmar_exclusao_id", None)
        await query.edit_message_text("👍 Exclusão cancelada. A tarefa continua ativa.")

