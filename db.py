import sqlite3
import datetime

# ---------------------- AUTH DB ----------------------

def init_auth_db():
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id INTEGER PRIMARY KEY,
            authorized_until TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_user_authorized(user_id):
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("SELECT authorized_until FROM authorized_users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    authorized_until = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    return authorized_until > datetime.datetime.now()

def authorize_user(user_id, months=4):
    until = datetime.datetime.now() + datetime.timedelta(days=30 * months)
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO authorized_users (user_id, authorized_until)
        VALUES (?, ?)
    """, (user_id, until.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ---------------------- KNOWLEDGE DB ----------------------

def init_knowledge_base_db():
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT UNIQUE,
            answer TEXT
        )
    """)
    conn.commit()
    conn.close()

def search_answer(question):
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM answers WHERE question = ?", (question,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_answer(question, answer):
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO answers (question, answer) VALUES (?, ?)", (question, answer))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Вопрос уже есть
    conn.close()

def search_related_answers(query):
    conn = sqlite3.connect("knowledge.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT question FROM answers
        WHERE question LIKE ?
        LIMIT 3
    """, (f"%{query}%",))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]