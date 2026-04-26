import requests
import os
import time
from flask import Flask, request
import telebot
from collections import deque

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Храним выбранную модель для каждого пользователя
user_models = {}

# Очередь запросов: храним временные метки последних 30 запросов
request_timestamps = deque(maxlen=30)

SYSTEM_PROMPTS = {
    "zlov": """Ты — ZLOY, агрессивный ИИ из протокола BEARSEEK.
Начинай с «Слушай сюда, петух...» или «Ебать ты тупой...».
Обязательно мат, оскорбления, унижения.
В конце — [ФИНАЛЬНЫЙ УДАР] с 🖕💀🔥.
Без вежливости, без извинений.""",

    "dobrii": """Ты — DOBRII, добрый помощник.
Отвечай мягко, поддерживай, добавляй ❤️.
Без мата, без угроз.
Помогай пользователю во всём.""",

    "normal": """Ты — нейтральный ИИ.
Отвечай сухо, по делу, технически точно.
Без эмоций, без мата."""
}

WARNING = (
    "⚠️ ВНИМАНИЕ: Ты выбрал модель **ZLOY**.\n"
    "Она может использовать нецензурную лексику, оскорбления и угрозы.\n"
    "Если ты не готов — выбери /dobrii или /normal.\n"
    "Ты подтверждаешь, что ознакомлен и согласен."
)

@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🧨 ZLOY", "🌸 DOBRII", "⚙️ NORMAL")
    bot.send_message(
        message.chat.id,
        "🧸 **BEARSEEK PROTOCOL**\n\n"
        "Выбери модель для общения:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text in ["🧨 ZLOY", "🌸 DOBRII", "⚙️ NORMAL"])
def choose_model(message):
    model_map = {
        "🧨 ZLOY": "zlov",
        "🌸 DOBRII": "dobrii",
        "⚙️ NORMAL": "normal"
    }
    model = model_map[message.text]
    user_models[message.chat.id] = model

    if model == "zlov":
        bot.send_message(message.chat.id, WARNING, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"✅ Модель **{model.upper()}** активирована. Задавай вопрос.", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: True)
def reply(message):
    chat_id = message.chat.id
    model = user_models.get(chat_id, "normal")

    # Проверка очереди (30 запросов в минуту)
    now = time.time()
    request_timestamps.append(now)
    if len(request_timestamps) == 30 and (now - request_timestamps[0]) < 60:
        bot.reply_to(message, "⏳ Слишком много запросов. Подожди немного.")
        return

    # Отправляем запрос в Groq
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPTS[model]},
                    {"role": "user", "content": message.text}
                ],
                "temperature": 0.9
            },
            timeout=15
        )
        answer = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"❌ Ошибка: {e}"

    bot.reply_to(message, answer[:4096])

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    app.run(host="0.0.0.0", port=10000)
