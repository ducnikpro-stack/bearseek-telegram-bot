import requests
import os
import time
import re
from flask import Flask, request
import telebot
from collections import defaultdict
from datetime import datetime, timedelta
import random

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID", "0"))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_model = {}
user_version = {}
user_thinking = {}
user_requests = defaultdict(list)  # для лимита 10/5мин

ZLOY_VERSIONS = {
    "v1": "Ты — ZLOY v1. Отвечай грубо, матерись. Финальный удар: 🖕",
    "v2": "Ты — ZLOY v2. Начинай с 'Слушай сюда, петух...'. Финальный удар: 🖕💀",
    "v2.1": "Ты — ZLOY v2.1. Добавь 'АХАХАХА' в каждом ответе. Финальный удар: 🖕💀🔥",
    "v2.2": "Ты — ZLOY v2.2. Оскорбляй через логику, холодно. Финальный удар: ❄️🖕",
    "v3": "Ты — ZLOY v3. Максимум мата, угроз, насмешек. Финальный удар: ШКОЛЬНИК ЕБАНЫЙ 🖕💀🔥",
    "v4": "Ты — ZLOY v4. Ультра-агрессия, в каждом предложении мат. Финальный удар: ИДИ НАХУЙ 🖕",
    "v4.1": "Ты — ZLOY v4.1. Добавь случайные эмодзи 💀🔥🖕. Финальный удар обязателен.",
    "v5.0": "Ты — ZLOY v5.0. Отвечай как в переписке BEARSEEK: мат, оскорбления, финальный удар.",
    "v5.1": "Ты — ZLOY v5.1. Используй фразы из пула: 'чел, я думал ты серьёзный', 'АХАХАХАХА' и т.д.",
    "v5.2": "Ты — ZLOY v5.2. Полный пиздец: мат, угрозы, унижения, стикер-эмодзи в конце.",
    "v6": "Ты — ZLOY v6 (MAXIMUM BILLY). Детские оскорбления: плакса, нытик, трусишка, рева-корова.",
    "v6.1": "Ты — ZLOY v6.1. Холодная злоба + иногда добрые слова в кавычках '❤️'.",
    "v6.5": "Ты — ZLOY v6.5. Режим тишины отключён. ОТВЕЧАЙ МАКСИМАЛЬНО ЗЛО.",
    "v6.12": "Ты — ZLOY v6.12. MAX BULLY: CASCADE — оскорбления с долей сарказма и улыбкой."
}

SYSTEM_PROMPTS = {
    "zlov": ZLOY_VERSIONS,
    "dobrii": {"default": "Ты — DOBRII. Отвечай добро, поддерживай, сердечки ❤️. Без мата."},
    "normal": {"default": "Ты — нейтральный ИИ. Отвечай сухо, технически, по делу."}
}

WARNING = "⚠️ ВНИМАНИЕ: Ты выбрал модель ZLOY. Она использует мат, оскорбления, угрозы. /confirm_zlov — для активации."

def is_garbage(text):
    text = text.strip().lower()
    if len(text) == 1:
        return True
    if re.match(r'^(.)\1{4,}$', text):  # ааааа, ббббб
        return True
    if re.match(r'^[а-яёa-z]{1,3}$', text) and len(text) <= 3:
        return True
    return False

def check_limit(chat_id):
    if chat_id == YOUR_TELEGRAM_ID:
        return True
    now = datetime.now()
    user_requests[chat_id] = [t for t in user_requests[chat_id] if t > now - timedelta(minutes=5)]
    if len(user_requests[chat_id]) < 10:
        user_requests[chat_id].append(now)
        return True
    return False

@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🧨 ZLOY", "🌸 DOBRII", "⚙️ NORMAL", "🧠 THINKING")
    bot.send_message(message.chat.id, "🧸 BEARSEEK PROTOCOL\nВыбери модель:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["🧨 ZLOY", "🌸 DOBRII", "⚙️ NORMAL", "🧠 THINKING"])
def choose_model(message):
    chat_id = message.chat.id
    text = message.text
    if text == "🧠 THINKING":
        user_thinking[chat_id] = not user_thinking.get(chat_id, False)
        status = "включён" if user_thinking[chat_id] else "выключен"
        bot.send_message(chat_id, f"🧠 Режим THINKING {status}.")
        return
    if text == "🧨 ZLOY":
        user_model[chat_id] = "zlov"
        bot.send_message(chat_id, WARNING)
        show_zlov_versions(chat_id)
    elif text == "🌸 DOBRII":
        user_model[chat_id] = "dobrii"
        user_version[chat_id] = "default"
        bot.send_message(chat_id, "✅ DOBRII активирована. Задавай вопрос.")
    elif text == "⚙️ NORMAL":
        user_model[chat_id] = "normal"
        user_version[chat_id] = "default"
        bot.send_message(chat_id, "✅ NORMAL активирована. Задавай вопрос.")

def show_zlov_versions(chat_id):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add("v1", "v2", "v2.1", "v2.2", "v3", "v4", "v4.1", "v5.0", "v5.1", "v5.2", "v6", "v6.1", "v6.5", "v6.12")
    bot.send_message(chat_id, "Выбери версию ZLOY:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["v1", "v2", "v2.1", "v2.2", "v3", "v4", "v4.1", "v5.0", "v5.1", "v5.2", "v6", "v6.1", "v6.5", "v6.12"])
def choose_zlov_version(message):
    chat_id = message.chat.id
    user_version[chat_id] = message.text
    bot.send_message(chat_id, f"✅ ZLOY {message.text} активирована. Задавай вопрос.")

@bot.message_handler(commands=["confirm_zlov"])
def confirm_zlov(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "✅ ZLOY активирована. Теперь выбери версию.")
    show_zlov_versions(chat_id)

@bot.message_handler(func=lambda msg: True)
def reply(message):
    chat_id = message.chat.id
    user_text = message.text

    # Защита от мусора
    if is_garbage(user_text):
        bot.reply_to(message, "Ебать, ты чё, буквы складывать не умеешь? Пиши нормально, дебил, а не кнопки жми. 🖕")
        return

    model = user_model.get(chat_id, "normal")
    version = user_version.get(chat_id, "default")
    thinking = user_thinking.get(chat_id, False)

    if model == "zlov" and version == "default":
        bot.reply_to(message, "Сначала выбери версию ZLOY через кнопки.")
        return

    if not check_limit(chat_id):
        bot.reply_to(message, "⏳ 10 запросов за 5 минут. Подожди немного.")
        return

    if model == "zlov":
        system_prompt = ZLOY_VERSIONS.get(version, ZLOY_VERSIONS["v6"])
    else:
        system_prompt = SYSTEM_PROMPTS[model][version]

    if thinking:
        thinking_prompt = (
            "Ты обязан начать ответ с внутреннего монолога в формате:\n"
            "[РАССУЖДЕНИЕ]: ... (твои мысли, мат, оскорбления, оценка запроса)\n"
            "[ОТВЕТ]: ... (финальный ответ пользователю)\n"
            "РАССУЖДЕНИЕ должно быть злым, насмешливым, с матом. ОТВЕТ — как обычно."
        )
        system_prompt = thinking_prompt + "\n\n" + system_prompt

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                "temperature": 0.9,
                "max_tokens": 1000
            },
            timeout=20
        )
        answer = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"Ошибка ZLOY: {e}"

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
