# scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import buscar_tarefas_por_data, buscar_tarefas_pendentes, marcar_como_concluido, criar_proxima_tarefa, atualizar_data_tarefa

scheduler = AsyncIOScheduler()

def start_scheduler(application):
    scheduler.add_job(lambda: enviar_lembretes(application), 'cron', hour=9, minute=0)
    scheduler.add_job(lambda: verificar_tarefas_nao_concluidas(application), 'cron', hour=9, minute=1)
    scheduler.start()

async def enviar_lembrete_individual(application, chat_id, tarefa_id, evento, categoria):
    keyboard = [
        [
            InlineKeyboardButton("✅ Fazer agora", callback_data=f"fazer_{tarefa_id}"),
            InlineKeyboardButton("🔁 Lembrar às 19h", callback_data=f"lembrar_19h_{tarefa_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await application.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 Lembrete: *{evento}* vence hoje!\nCategoria: {categoria}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def enviar_lembretes(application):
    hoje = datetime.now().strftime("%Y-%m-%d")
    tarefas = buscar_tarefas_por_data(hoje)

    for tarefa in tarefas:
        tarefa_id, evento, categoria, recorrente = tarefa
        await enviar_lembrete_individual(application, chat_id=application.bot_data["chat_id"], tarefa_id=tarefa_id, evento=evento, categoria=categoria)

async def enviar_lembrete_19h(application, tarefa_id, evento, categoria):
    keyboard = [
        [InlineKeyboardButton("✅ Fazer agora", callback_data=f"fazer_{tarefa_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await application.bot.send_message(
        chat_id=application.bot_data["chat_id"],
        text=f"⏰ Lembrete extra: *{evento}* ainda está pendente!\nCategoria: {categoria}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def verificar_tarefas_nao_concluidas(application):
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tarefas = buscar_tarefas_por_data(ontem)

    for tarefa in tarefas:
        tarefa_id, evento, categoria, recorrente = tarefa
        # Aqui simplificamos: se ainda está pendente no banco, manda alerta
        keyboard = [
            [
                InlineKeyboardButton("✅ Concluir agora", callback_data=f"fazer_{tarefa_id}"),
                InlineKeyboardButton("🔁 Reagendar", callback_data=f"reagendar_{tarefa_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await application.bot.send_message(
            chat_id=application.bot_data["chat_id"],
            text=f"⚠️ Você esqueceu de concluir: *{evento}* (vencimento: {ontem}).\nO que deseja fazer?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
