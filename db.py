# db.py

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def conectar():
    return psycopg2.connect(DATABASE_URL)

def criar_tabela():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id SERIAL PRIMARY KEY,
                evento TEXT NOT NULL,
                data_vencimento DATE NOT NULL,
                recorrente BOOLEAN NOT NULL,
                categoria TEXT,
                status TEXT DEFAULT 'pendente',
                lembrete_enviado BOOLEAN DEFAULT FALSE
            );
        """)
        conn.commit()

def adicionar_tarefa(evento, data_vencimento, recorrente, categoria):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tarefas (evento, data_vencimento, recorrente, categoria, status, lembrete_enviado)
            VALUES (%s, %s, %s, %s, 'pendente', FALSE);
        """, (evento, data_vencimento, recorrente, categoria))
        conn.commit()

    
def buscar_tarefas_por_data(data):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, evento, categoria, recorrente FROM tarefas
            WHERE data_vencimento = %s
            AND status = 'pendente';
        """, (data,))
        return cursor.fetchall()

def marcar_como_concluido(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tarefas
            SET status = 'concluido'
            WHERE id = %s;
        """, (tarefa_id,))
        conn.commit()

def criar_proxima_tarefa(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT evento, data_vencimento, recorrente, categoria FROM tarefas
            WHERE id = %s;
        """, (tarefa_id,))
        tarefa = cursor.fetchone()

        if tarefa:
            evento, data_vencimento, recorrente, categoria = tarefa
            if recorrente:
                nova_data = calcular_mes_seguinte(data_vencimento)
                adicionar_tarefa(evento, nova_data, recorrente, categoria)

def marcar_lembrete_enviado(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tarefas
            SET lembrete_enviado = TRUE
            WHERE id = %s;
        """, (tarefa_id,))
        conn.commit()
        
def calcular_mes_seguinte(data_str):
    if isinstance(data_str, str):
        data = datetime.strptime(data_str, "%Y-%m-%d")
    else:
        data = data_str  # já é datetime

    ano = data.year + (data.month // 12)
    mes = (data.month % 12) + 1
    dia = data.day

    try:
        nova_data = datetime(ano, mes, dia)
    except ValueError:
        if mes == 2:
            dia = 28
        elif mes in [4, 6, 9, 11]:
            dia = 30
        else:
            dia = 31
        nova_data = datetime(ano, mes, dia)

    return nova_data.date()

def buscar_tarefas_pendentes():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, evento, data_vencimento, categoria FROM tarefas
            WHERE status = 'pendente'
            ORDER BY data_vencimento ASC;
        """)
        return cursor.fetchall()

def atualizar_data_tarefa(tarefa_id, nova_data):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tarefas
            SET data_vencimento = %s, lembrete_enviado = FALSE
            WHERE id = %s;
        """, (nova_data, tarefa_id))
        conn.commit()
        
def atualizar_tarefa(tarefa_id, campo, valor):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tarefas SET {campo} = %s WHERE id = %s;", (valor, tarefa_id))
        conn.commit()
    
def deletar_tarefa(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tarefas WHERE id = %s;", (tarefa_id,))
        conn.commit()

def buscar_tarefa_por_id(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT evento, categoria FROM tarefas
            WHERE id = %s;
        """, (tarefa_id,))
        return cursor.fetchone()
