# scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import (
    buscar_tarefas_por_data,
    marcar_lembrete_enviado,
    buscar_tarefa_por_id,
)

scheduler = AsyncIOScheduler()

def start_scheduler(application):
    # Lembretes às 09h
    scheduler.add_job(lambda: enviar_lembretes(application, horario="manha"), 'cron', hour=9, minute=0)
    
    # Reenvio às 19h (somente pendentes)
    scheduler.add_job(lambda: enviar_lembretes(application, horario="noite"), 'cron', hour=19, minute=0)

    scheduler.start()

async def enviar_lembrete_individual(application, chat_id, tarefa_id, evento, categoria, is_reforco=False):
    if is_reforco:
        keyboard = [[InlineKeyboardButton("✅ Fazer agora", callback_data=f"fazer_{tarefa_id}")]]
        texto = f"⏰ Lembrete extra: *{evento}* ainda está pendente!\nCategoria: {categoria}"
    else:
        keyboard = [
            [
                InlineKeyboardButton("✅ Fazer agora", callback_data=f"fazer_{tarefa_id}"),
                InlineKeyboardButton("🔁 Lembrar às 19h", callback_data=f"lembrar_19h_{tarefa_id}")
            ]
        ]
        texto = f"🔔 Lembrete: *{evento}* vence hoje!\nCategoria: {categoria}"

    await application.bot.send_message(
        chat_id=chat_id,
        text=texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def enviar_lembretes(application, horario="manha"):
    hoje = datetime.now().strftime("%Y-%m-%d")
    tarefas = buscar_tarefas_por_data(hoje)

    for tarefa in tarefas:
        tarefa_id, evento, categoria, recorrente = tarefa

        if horario == "manha":
            # Envio principal e marca como enviado
            await enviar_lembrete_individual(
                application,
                chat_id=application.bot_data["chat_id"],
                tarefa_id=tarefa_id,
                evento=evento,
                categoria=categoria
            )
            marcar_lembrete_enviado(tarefa_id)

        elif horario == "noite":
            # Reenvio se ainda estiver pendente
            tarefa_info = buscar_tarefa_por_id(tarefa_id)
            if tarefa_info:
                await enviar_lembrete_individual(
                    application,
                    chat_id=application.bot_data["chat_id"],
                    tarefa_id=tarefa_id,
                    evento=evento,
                    categoria=categoria,
                    is_reforco=True
                )
