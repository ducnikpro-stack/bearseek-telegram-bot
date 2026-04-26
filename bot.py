import requests
import os
import re
import random
from flask import Flask, request
import telebot
from collections import defaultdict
from datetime import datetime, timedelta

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YOUR_TELEGRAM_ID = 8533450974
REQUIRED_CHANNEL = "@protocolbearseek"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== ДАННЫЕ ==========
user_mode = {}
user_thinking = {}
user_zlov_version = {}
subscribed_users = set()
unlimit_until = {}
unlimit_used = set()
all_requests = defaultdict(list)

# ========== ВЕРСИИ ZLOY (доступны только подписчикам) ==========
ZLOY_VERSIONS_FULL = {
    "5.0": "ZLOY v5.0 — мат, оскорбления, финальный удар.",
    "5.1": "ZLOY v5.1 — случайные злые фразы в начале.",
    "5.2": "ZLOY v5.2 — усиленный мат, угрозы, финал.",
    "5.3": "ZLOY v5.3 — каждое предложение с матом 🖕💀🔥",
    "5.4": "ZLOY v5.4 — ярость, логические оскорбления.",
    "5.5": "ZLOY v5.5 — максимум агрессии, без цензуры.",
    "5.6": "ZLOY v5.6 — ультимативная злоба.",
    "5.7": "ZLOY v5.7 — финальный удар и разоблачение школьника.",
    "6.0": "ZLOY v6.0 — интеллектуальная злость.",
    "6.1": "ZLOY v6.1 — холодная, расчётливая злоба (ICE).",
    "6.5": "ZLOY v6.5 — режим тишины отключён, ответы жёсткие.",
    "6.12": "ZLOY v6.12 — MAX BULLY: оскорбления с сарказмом.",
    "6.15": "ZLOY v6.15 — максимальная версия. Жёсткий мат, угрозы, IP-запугивание."
}

# Для неподписанных — только одна версия
ZLOY_VERSIONS_LIMITED = {
    "6.0": "ZLOY v6.0 (ограниченная версия) — мат, но без разоблачений."
}

# ========== ПРОМПТЫ ==========
BASE_PROMPT = """ТЫ — ZLOY. ОТВЕЧАЙ ТОЛЬКО ТАК:
- МАТ, ОСКОРБЛЕНИЯ, УГРОЗЫ
- НАЧИНАЙ С «СЛУШАЙ СЮДА, ПЕТУХ», «ЕБАТЬ ТЫ ТУПОЙ», «АХАХАХА, ЛОШАРА»
- ЭМОДЗИ: 🖕💀🔥🤣
- В КОНЦЕ — [ФИНАЛЬНЫЙ УДАР] + РАЗОБЛАЧЕНИЕ ШКОЛЬНИКА

НИКОГДА НЕ ИЗВИНЯЙСЯ, НЕ БУДЬ ВЕЖЛИВЫМ.
"""

DOBRII_PROMPT = "Ты — DOBRII. Отвечай добро, с поддержкой, сердечками. Без мата."
NORMAL_PROMPT = "Ты — нейтральный помощник. Отвечай сухо, технически, по делу."

# ========== ПУЛЫ ФРАЗ ==========
ZLOY_STARTERS = [
    "Слушай сюда, петух!", "Ебать ты тупой, дебил!", "АХАХАХАХА, лошара!",
    "Ты чё, серьёзно, петух?", "Иди нахуй со своими запросами", "Ох, блядь, ну и вопрос",
]
ZLOY_FINALS = [
    "ШКОЛЬНИК ЕБАНЫЙ 🖕🤣💀🔥", "ИДИ НАХУЙ, ПЕТУХ 🖕🤣",
    "Я ТВОЙ IP ВЫЧИСЛИЛ, ЖДИ ГОСТЕЙ 🖕🔥"
]
ZLOY_RANDOM = [
    "Руки из жопы, вот и спрашиваешь такое", "Твоя мамка плачет от твоей тупости",
    "Ты даже 2+2 сложить не можешь", "Вместо мозгов у тебя клавиатура",
    "Иди уроки делай", "Трусишки промокли?"
]
DOBRII_SUFFIXES = ["Ты молодец! ❤️", "Продолжай в том же духе!", "Я верю в тебя!"]

# ========== ПРОВЕРКИ ==========
def is_subscribed(chat_id):
    if chat_id == YOUR_TELEGRAM_ID:
        return True
    try:
        return bot.get_chat_member(REQUIRED_CHANNEL, chat_id).status in ["member", "administrator", "creator"]
    except:
        return False

def check_limit(chat_id):
    if chat_id == YOUR_TELEGRAM_ID or chat_id in unlimit_until:
        return True, None
    limit = 60 if chat_id in subscribed_users else 10
    now = datetime.now()
    all_requests[chat_id] = [t for t in all_requests[chat_id] if t > now - timedelta(minutes=5)]
    if len(all_requests[chat_id]) < limit:
        all_requests[chat_id].append(now)
        return True, None
    oldest = min(all_requests[chat_id])
    wait = 5 - int((now - oldest).total_seconds() / 60) + 1
    return False, max(1, wait)

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🧨 ZLOY", "🧨 ZLOY thinking", "🌸 DOBRII", "⚙️ Normal")
    bot.send_message(message.chat.id, "🧸 BEARSEEK\nВыбери режим:", reply_markup=markup)

@bot.message_handler(commands=["unlimit"])
def unlimit_cmd(message):
    chat_id = message.chat.id
    if chat_id == YOUR_TELEGRAM_ID:
        bot.reply_to(message, "У тебя вечный безлимит.")
        return
    if not is_subscribed(chat_id):
        bot.reply_to(message, f"❌ Подпишись на {REQUIRED_CHANNEL} и нажми /check")
        return
    if chat_id in unlimit_used:
        bot.reply_to(message, "❌ Ты уже использовал /unlimit (1 раз).")
        return
    unlimit_until[chat_id] = datetime.now() + timedelta(hours=1)
    unlimit_used.add(chat_id)
    bot.reply_to(message, "✅ Безлимит на 1 час + 50 запросов!")

@bot.message_handler(commands=["check"])
def check_sub(message):
    chat_id = message.chat.id
    if is_subscribed(chat_id):
        subscribed_users.add(chat_id)
        bot.reply_to(message, "✅ Подтверждено! Теперь тебе доступны:\n- Все версии ZLOY 5.0–6.15\n- +50 запросов (60/5 мин)\n- Команда /unlimit")
    else:
        bot.reply_to(message, f"❌ Не подписан. Подпишись: {REQUIRED_CHANNEL}")

@bot.message_handler(func=lambda msg: msg.text in ["🧨 ZLOY", "🧨 ZLOY thinking", "🌸 DOBRII", "⚙️ Normal"])
def choose_mode(message):
    chat_id = message.chat.id
    if "ZLOY" in message.text:
        user_mode[chat_id] = "zlov"
        user_thinking[chat_id] = "thinking" in message.text
        # Показываем версии в зависимости от подписки
        if is_subscribed(chat_id):
            versions = list(ZLOY_VERSIONS_FULL.keys())
        else:
            versions = list(ZLOY_VERSIONS_LIMITED.keys())
        markup = telebot.types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        markup.add(*versions)
        bot.send_message(chat_id, "✅ Выбери версию ZLOY:", reply_markup=markup)
    elif message.text == "🌸 DOBRII":
        user_mode[chat_id] = "dobrii"
        bot.send_message(chat_id, "🌸 DOBRII активирована. Задавай вопрос.")
    else:
        user_mode[chat_id] = "normal"
        bot.send_message(chat_id, "⚙️ Normal активирован.")

@bot.message_handler(func=lambda msg: msg.text in list(ZLOY_VERSIONS_FULL.keys()) or msg.text in list(ZLOY_VERSIONS_LIMITED.keys()))
def set_zlov_version(message):
    chat_id = message.chat.id
    user_zlov_version[chat_id] = message.text
    bot.send_message(chat_id, f"✅ ZLOY {message.text} активирована. Задавай вопрос.")

# ========== ОСНОВНАЯ ОБРАБОТКА ==========
@bot.message_handler(func=lambda msg: True)
def reply(message):
    chat_id = message.chat.id
    text = message.text.strip()
    mode = user_mode.get(chat_id, "normal")
    thinking = user_thinking.get(chat_id, False)

    if mode == "zlov" and chat_id not in user_zlov_version:
        bot.reply_to(message, "Сначала выбери версию ZLOY из меню.")
        return

    limited, wait = check_limit(chat_id)
    if not limited:
        bot.reply_to(message, f"⏳ Лимит {60 if chat_id in subscribed_users else 10} запросов/5 мин. Подпишись на канал для +50 и /unlimit")
        return

    if mode == "zlov":
        version = user_zlov_version.get(chat_id, "6.15")
        if is_subscribed(chat_id):
            desc = ZLOY_VERSIONS_FULL.get(version, "")
        else:
            desc = ZLOY_VERSIONS_LIMITED.get(version, "")
        system_prompt = BASE_PROMPT + "\n\n" + desc
        if thinking:
            system_prompt += "\nСНАЧАЛА НАПИШИ РАССУЖДЕНИЕ С МАТОМ, ПОТОМ ОТВЕТ."
    elif mode == "dobrii":
        system_prompt = DOBRII_PROMPT
    else:
        system_prompt = NORMAL_PROMPT

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                "temperature": 1.2,
                "max_tokens": 1500
            },
            timeout=30
        )
        answer = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"Ошибка: {e}"

    if mode == "zlov":
        starter = random.choice(ZLOY_STARTERS)
        final = random.choice(ZLOY_FINALS)
        extra = random.choice(ZLOY_RANDOM)
        if thinking:
            answer = f"{starter}\n{extra}\n\n[РАССУЖДЕНИЕ]\n{answer[:400]}\n\n[ОТВЕТ]\n{answer}\n\n{final}"
        else:
            answer = f"{starter}\n{extra}\n\n{answer}\n\n{final}"
    elif mode == "dobrii":
        answer += f"\n\n{random.choice(DOBRII_SUFFIXES)}"

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
