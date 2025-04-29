# db.py

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "tarefas.db"

def conectar():
    return sqlite3.connect(DB_FILE)

def criar_tabela():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                recorrente BOOLEAN NOT NULL,
                categoria TEXT,
                status TEXT DEFAULT 'pendente',
                lembrete_enviado BOOLEAN DEFAULT 0
            );
        """)
        conn.commit()

def adicionar_tarefa(evento, data_vencimento, recorrente, categoria):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tarefas (evento, data_vencimento, recorrente, categoria, status, lembrete_enviado)
            VALUES (?, ?, ?, ?, 'pendente', 0);
        """, (evento, data_vencimento, recorrente, categoria))
        conn.commit()

def buscar_tarefas_por_data(data):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, evento, categoria, recorrente FROM tarefas
            WHERE date(data_vencimento) = date(?)
            AND status = 'pendente';
        """, (data,))
        return cursor.fetchall()
        
def buscar_tarefa_por_id(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT evento, categoria FROM tarefas
            WHERE id = ?;
        """, (tarefa_id,))
        return cursor.fetchone()
        
def marcar_como_concluido(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tarefas
            SET status = 'concluido'
            WHERE id = ?;
        """, (tarefa_id,))
        conn.commit()

def criar_proxima_tarefa(tarefa_id):
    """Quando concluir uma tarefa recorrente, cria a próxima no mês seguinte"""
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT evento, data_vencimento, recorrente, categoria FROM tarefas
            WHERE id = ?;
        """, (tarefa_id,))
        tarefa = cursor.fetchone()

        if tarefa:
            evento, data_vencimento, recorrente, categoria = tarefa
            if recorrente:
                nova_data = calcular_mes_seguinte(data_vencimento)
                adicionar_tarefa(evento, nova_data, recorrente, categoria)

def calcular_mes_seguinte(data_str):
    """Calcula a mesma data no próximo mês, ajustando se for fim de mês."""
    data = datetime.strptime(data_str, "%Y-%m-%d")
    ano = data.year + (data.month // 12)
    mes = (data.month % 12) + 1
    dia = data.day

    try:
        nova_data = datetime(ano, mes, dia)
    except ValueError:
        # Se não existir (ex.: 31 de fevereiro), ajusta para último dia do mês
        if mes == 2:
            dia = 28
        elif mes in [4, 6, 9, 11]:
            dia = 30
        else:
            dia = 31
        nova_data = datetime(ano, mes, dia)

    return nova_data.strftime("%Y-%m-%d")

def buscar_tarefas_pendentes():
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, evento, data_vencimento, categoria FROM tarefas
            WHERE status = 'pendente';
        """)
        return cursor.fetchall()

def atualizar_data_tarefa(tarefa_id, nova_data):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tarefas
            SET data_vencimento = ?, lembrete_enviado = 0
            WHERE id = ?;
        """, (nova_data, tarefa_id))
        conn.commit()

def deletar_tarefa(tarefa_id):
    with conectar() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM tarefas WHERE id = ?;
        """, (tarefa_id,))
        conn.commit()
