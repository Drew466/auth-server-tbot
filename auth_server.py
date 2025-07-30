from flask import Flask, request, redirect, render_template, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")  # Пароль из .env

DB_PATH = "auth_users.db"


def init_auth_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id INTEGER PRIMARY KEY,
            auth_date TEXT
        )
    ''')
    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")

        if password == AUTH_PASSWORD:
            return render_template("success.html")
        else:
            return render_template("login.html", error="❌ Неверный пароль")

    return render_template("login.html")


@app.route("/authorize/<int:user_id>")
def authorize(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute("REPLACE INTO authorized_users (user_id, auth_date) VALUES (?, ?)", (user_id, now))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/check/<int:user_id>")
def check(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT auth_date FROM authorized_users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        auth_date = datetime.fromisoformat(result[0])
        if datetime.now() - auth_date <= timedelta(days=120):  # 4 месяца
            return jsonify({"authorized": True})

    return jsonify({"authorized": False})


if name == "__main__":
    init_auth_db()
    app.run(debug=True)