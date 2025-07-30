import os
import sqlite3
import requests
import telebot
from telebot import types
from dotenv import load_dotenv
from db import (
    init_auth_db,
    init_knowledge_base_db,
    is_user_authorized,
    authorize_user,
    search_answer,
    save_answer,
    search_related_answers
)
from pydub import AudioSegment
import tempfile
import time

load_dotenv()

init_auth_db()
init_knowledge_base_db()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
AUTH_SERVER_URL = os.getenv("AUTH_SERVER_URL")
MODEL = "mistralai/mistral-7b-instruct"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def ask_openrouter(user_question, db_answer):
    if db_answer:
        system_prompt = f"Ты - Ai-ассистент Т-банка.\nВот информация из базы данных:\nВопрос: {user_question}\nОтвет: {db_answer}\nОтветь кратко и по делу. Если недостаточно - дополни по своим знаниям."
    else:
        system_prompt = f"Ты - краткий и понятный AI-ассистент.\nНа вопрос \"{user_question}\" в базе нет ответа.\nСформулируй ответ, но обязательно укажи в начале, что он основан не из базы знаний."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://t.me/your_bot_username",
        "X-Title": "TelegramBot"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("❌ Ошибка при запросе к GPT:", e)
        return "Произошла ошибка при получении ответа от GPT."

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id

    if not is_user_authorized(user_id):
        bot.send_message(
            message.chat.id,
            f"🔐 Для доступа авторизуйтесь:\n{AUTH_SERVER_URL}"
        )
        return

    user_question = message.text.strip()
    db_answer = search_answer(user_question)
    gpt_answer = ask_openrouter(user_question, db_answer)

    if not db_answer and "Произошла ошибка" not in gpt_answer:
        save_answer(user_question, gpt_answer)

    reply_text = gpt_answer

    related = search_related_answers(user_question)
    if related:
        reply_text += "\n\n📌 Похожие темы:\n"
        for q in related:
            reply_text += f"• {q}\n"

    bot.send_message(message.chat.id, reply_text)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id

    if not is_user_authorized(user_id):
        bot.send_message(
            message.chat.id,
            f"🔐 Для доступа авторизуйтесь:\n{AUTH_SERVER_URL}"
        )
        return

    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as ogg_file:
            ogg_file.write(downloaded_file)
            ogg_path = ogg_file.name

        mp3_path = ogg_path.replace(".ogg", ".mp3")
        AudioSegment.from_ogg(ogg_path).export(mp3_path, format="mp3")

        with open(mp3_path, 'rb') as f:
            headers = {'authorization': ASSEMBLYAI_API_KEY}
            upload_response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, files={'file': f})
            audio_url = upload_response.json()['upload_url']

        json_data = {'audio_url': audio_url, 'language_code': 'ru'}
        transcript_response = requests.post("https://api.assemblyai.com/v2/transcript", json=json_data, headers=headers)
        transcript_id = transcript_response.json()['id']

        status = 'queued'
        while status not in ['completed', 'error']:
            poll_response = requests.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers)
            status = poll_response.json()['status']
            time.sleep(2)

        if status == 'completed':
            user_question = poll_response.json()['text']
            bot.send_message(message.chat.id, f"🎙️ Распознанный текст:\n{user_question}")

            db_answer = search_answer(user_question)
            gpt_answer = ask_openrouter(user_question, db_answer)

            if not db_answer and "Произошла ошибка" not in gpt_answer:
                save_answer(user_question, gpt_answer)

            reply_text = gpt_answer

            related = search_related_answers(user_question)
            if related:
                reply_text += "\n\n📌 Похожие темы:\n"
                for q in related:
                    reply_text += f"• {q}\n"

            bot.send_message(message.chat.id, reply_text)
        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось распознать аудио.")

    except Exception as e:
        print("❌ Ошибка при голосовом:", e)
        bot.send_message(message.chat.id, "⚠️ Ошибка при обработке голосового сообщения.")

if __name__ == "__main__":
    try:
        print("✅ Бот запущен и работает!")
        bot.polling()
    except Exception as e:
        print("❌ Ошибка запуска:", e)
