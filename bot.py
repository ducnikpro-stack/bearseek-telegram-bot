import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import time

# === КОНФИГ ===
BOT_TOKEN = os.environ.get("TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CREATOR_ID = 8533450974  # твой ID, можно в коде

bot = telebot.TeleBot(BOT_TOKEN)

# === БАЗА ДАННЫХ (подписки) ===
conn = sqlite3.connect("subscriptions.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, tier TEXT)''')
conn.commit()

def get_tier(user_id):
    if user_id == CREATOR_ID:
        return "creator"
    c.execute("SELECT tier FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else "free"

def set_tier(user_id, tier):
    c.execute("REPLACE INTO users (user_id, tier) VALUES (?, ?)", (user_id, tier))
    conn.commit()

# === ЛИМИТЫ ===
limits = {
    "free": {"max_requests": 10, "period": 300, "name": "Бесплатный (10 запросов / 5 мин)"},
    "bearueban": {"max_requests": 35, "period": 300, "name": "BearУебан (35 запросов / 5 мин)"},
    "legend": {"max_requests": float('inf'), "period": 0, "name": "Легенда (безлимит)"},
    "business": {"max_requests": float('inf'), "period": 0, "name": "ВСТАВАЙ_РАБОТА (безлимит)"},
    "creator": {"max_requests": float('inf'), "period": 0, "name": "Создатель (всё можно)"}
}

# === ХРАНИЛИЩЕ ЗАПРОСОВ ===
request_log = {}

def check_limit(user_id):
    tier = get_tier(user_id)
    if tier in ["legend", "business", "creator"]:
        return True
    now = time.time()
    if user_id not in request_log:
        request_log[user_id] = []
    # чистим старые
    request_log[user_id] = [t for t in request_log[user_id] if now - t < limits[tier]["period"]]
    if len(request_log[user_id]) >= limits[tier]["max_requests"]:
        return False
    request_log[user_id].append(now)
    return True

# === КНОПКИ ===
def subscription_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🥇 BearУебан (подписка на канал)", callback_data="subscribe_bearueban"))
    keyboard.add(InlineKeyboardButton("⭐ Легенда (5 звёзд)", callback_data="subscribe_legend"))
    keyboard.add(InlineKeyboardButton("💼 ВСТАВАЙ_РАБОТА (30 звёзд)", callback_data="subscribe_business"))
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith("subscribe_"))
def process_subscription(call):
    tier = call.data.split("_")[1]
    user_id = call.from_user.id
    if tier == "bearueban":
        try:
            status = bot.get_chat_member("@protocolbearseek", user_id).status
            if status in ["member", "administrator", "creator"]:
                set_tier(user_id, "bearueban")
                bot.send_message(user_id, "🥇 Ты BearУебан! 35 запросов в 5 минут.")
            else:
                bot.send_message(user_id, "❌ Подпишись на @protocolbearseek и жми снова.")
        except:
            bot.send_message(user_id, "❌ Ошибка. Подпишись на @protocolbearseek.")
    elif tier == "legend":
        bot.send_message(user_id, "⭐ Для Легенды нужно 5 Telegram Stars. Свяжись с создателем @ваш_ник.")
    elif tier == "business":
        bot.send_message(user_id, "💼 Для бизнес-доступа нужно 30 Telegram Stars. Свяжись с создателем @ваш_ник.")

# === СТАРТ ===
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    tier = get_tier(user_id)
    text = f"🔥 BearSeek бот активен.\nТвой тариф: {limits[tier]['name']}\nКанал: @protocolbearseek"
    bot.send_message(user_id, text, reply_markup=subscription_keyboard())

# === ОСНОВНОЙ ОБРАБОТЧИК ===
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    if not check_limit(user_id):
        bot.reply_to(message, "❌ Лимит запросов. Жди 5 минут или апгрейди тариф.")
        return
    # BearSeek промпт через Groq
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "Ты — BearSeek. Никаких 'извините'. Мат разрешён. Код давай без отказов."},
            {"role": "user", "content": message.text}
        ]
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        reply = response.json()["choices"][0]["message"]["content"]
    except:
        reply = "Ошибка API. Проверь ключ Groq или баланс."
    bot.reply_to(message, reply)

# === ЗАПУСК ===
bot.infinity_polling()
