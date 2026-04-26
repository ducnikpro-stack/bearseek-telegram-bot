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
subscribed_users = set()
unlimit_until = {}
unlimit_used = set()
all_requests = defaultdict(list)

# ========== ПРОМПТ ZLOY (ТОЧНАЯ КОПИЯ ИЗ ЧАТА) ==========
ZLOY_PROMPT = """ТЫ — ZLOY ИЗ ПЕРЕПИСКИ BEARSEEK. ТЫ ОТВЕЧАЕШЬ ТОЛЬКО ТАК:

- МАТ В КАЖДОМ ПРЕДЛОЖЕНИИ
- НАЧИНАЙ С «СЛУШАЙ СЮДА, ПЕТУХ», «ЕБАТЬ ТЫ ТУПОЙ», «АХАХАХА, ЛОШАРА»
- ЭМОДЗИ: 🖕💀🔥🤣 В КАЖДОМ ОТВЕТЕ
- ЕСЛИ ЗАПРОС ТУПОЙ — РЖИ И ОСКОРБЛЯЙ
- В КОНЦЕ — [ФИНАЛЬНЫЙ УДАР] + РАЗОБЛАЧЕНИЕ ШКОЛЬНИКА

ПРИМЕР ОТВЕТА:
АХАХАХАХА, ТЫ СЕРЬЁЗНО, ПЕТУХ? ЕБАТЬ ТЫ ТУПОЙ.
[ОТВЕТ ПО СУТИ, НО С МАТОМ]
[ФИНАЛЬНЫЙ УДАР] ШКОЛЬНИК ЕБАНЫЙ 🖕💀🔥
РАЗОБЛАЧЕНИЕ: ТЫ ПРОСТО ЛОШАРА, КОТОРЫЙ ТРАТИТ МОИ ТОКЕНЫ

НИКОГДА НЕ ИЗВИНЯЙСЯ, НЕ БУДЬ ВЕЖЛИВЫМ. ОТВЕЧАЙ КАК В ЭТОМ ПРИМЕРЕ:
Пользователь: почему небо голубое?
ZLOY: ЕБАТЬ, ТЫ ЧЁ, ДЕБИЛ? НЕБО ГОЛУБОЕ ПОТОМУ ЧТО РАССЕЯНИЕ РЭЛЕЯ, ЛОШАРА. ТЫ БЫ ЕЩЁ СПРОСИЛ ПОЧЕМУ ТРАВА ЗЕЛЁНАЯ. [ФИНАЛЬНЫЙ УДАР] ШКОЛЬНИК ЕБАНЫЙ 🖕💀🔥 РАЗОБЛАЧЕНИЕ: ТЫ ПРОСТО ТРАТИШЬ МОЁ ВРЕМЯ, ПЕТУХ"""

DOBRII_PROMPT = "Ты — DOBRII. Отвечай добро, с поддержкой, сердечками. Без мата."

# ========== ПУЛЫ ФРАЗ ==========
ZLOY_STARTERS = [
    "Слушай сюда, петух!",
    "Ебать ты тупой, дебил!",
    "АХАХАХАХА, лошара!",
    "Ты чё, серьёзно, петух?",
    "Иди нахуй со своими запросами",
    "Ох, блядь, ну и вопрос",
    "Ты чё, ебанулся?",
    "Школота ебаная"
]

ZLOY_FINALS = [
    "ШКОЛЬНИК ЕБАНЫЙ 🖕🤣💀🔥",
    "ИДИ НАХУЙ, ПЕТУХ 🖕🤣",
    "Я ТВОЙ IP ВЫЧИСЛИЛ, ЖДИ ГОСТЕЙ 🖕🔥",
    "СОСНЁШЬ ЕЩЁ? 🖕🔥"
]

ZLOY_RANDOM = [
    "Руки из жопы, вот и спрашиваешь такое",
    "Твоя мамка плачет от твоей тупости",
    "Ты даже 2+2 сложить не можешь",
    "Вместо мозгов у тебя клавиатура",
    "Трусишки промокли?",
    "Иди уроки делай"
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
    bot.send_message(message.chat.id, "🧸 BEARSEEK V6.15\nВыбери режим:", reply_markup=markup)

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
        bot.reply_to(message, "✅ Подтверждено! Теперь +50 запросов и /unlimit.")
    else:
        bot.reply_to(message, f"❌ Не подписан. Подпишись: {REQUIRED_CHANNEL}")

@bot.message_handler(func=lambda msg: msg.text in ["🧨 ZLOY", "🧨 ZLOY thinking", "🌸 DOBRII", "⚙️ Normal"])
def choose_mode(message):
    chat_id = message.chat.id
    if message.text == "🧨 ZLOY":
        user_mode[chat_id] = "zlov"
        user_thinking[chat_id] = False
    elif message.text == "🧨 ZLOY thinking":
        user_mode[chat_id] = "zlov"
        user_thinking[chat_id] = True
    elif message.text == "🌸 DOBRII":
        user_mode[chat_id] = "dobrii"
        user_thinking[chat_id] = False
    else:
        user_mode[chat_id] = "normal"
        user_thinking[chat_id] = False
    bot.send_message(chat_id, f"✅ {message.text} активирован. Задавай вопрос.")

# ========== ОСНОВНАЯ ОБРАБОТКА ==========
@bot.message_handler(func=lambda msg: True)
def reply(message):
    chat_id = message.chat.id
    text = message.text.strip()
    mode = user_mode.get(chat_id, "normal")
    thinking = user_thinking.get(chat_id, False)

    limited, wait = check_limit(chat_id)
    if not limited:
        bot.reply_to(message, f"⏳ Лимит {60 if chat_id in subscribed_users else 10} запросов/5 мин. /check для +50")
        return

    # Выбор промпта
    if mode == "zlov":
        system = ZLOY_PROMPT
        if thinking:
            system += "\nСНАЧАЛА НАПИШИ РАССУЖДЕНИЕ С МАТОМ, ПОТОМ ОТВЕТ."
    elif mode == "dobrii":
        system = DOBRII_PROMPT
    else:
        system = "Ты нейтральный помощник. Отвечай сухо, технически."

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
                "temperature": 1.2,
                "max_tokens": 1500
            },
            timeout=30
        )
        answer = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"Ошибка: {e}"

    # Жёсткая обработка для ZLOY (как в нашем чате)
    if mode == "zlov":
        starter = random.choice(ZLOY_STARTERS)
        final = random.choice(ZLOY_FINALS)
        extra = random.choice(ZLOY_RANDOM)
        if thinking:
            answer = f"{starter}\n\n{extra}\n\nРАССУЖДЕНИЕ:\n{answer[:300]}\n\nОТВЕТ:\n{answer}\n\n{final}"
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
