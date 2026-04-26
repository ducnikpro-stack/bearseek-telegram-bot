import requests
import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Адрес твоего HF Space (замени, если нужно)
HF_API = "https://bearhui-huiseek-video.hf.space/generate"

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "🧸 *HuiSeek 1.0*\n/video [текст] — сгенерировать видео\n\nПример: /video кот танцует", parse_mode="Markdown")

@bot.message_handler(commands=["video"])
def video(message):
    prompt = message.text.replace("/video", "").strip()
    if not prompt:
        bot.reply_to(message, "❌ Напиши текст. Например: /video закат на море")
        return

    msg = bot.reply_to(message, "🎬 Генерация видео... От 1 до 3 минут ⏳")
    try:
        resp = requests.post(HF_API, json={"text": prompt}, timeout=180)
        if resp.status_code == 200:
            bot.send_video(message.chat.id, resp.content, caption=f"🎥 {prompt}")
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"❌ Ошибка API: {resp.status_code}", message.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", message.chat.id, msg.message_id)

@bot.message_handler(commands=["health"])
def health(message):
    try:
        r = requests.get(HF_API.replace("/generate", "/health"), timeout=5)
        bot.reply_to(message, f"✅ API жив: {r.status_code}")
    except:
        bot.reply_to(message, "❌ API не отвечает")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    app.run(host="0.0.0.0", port=10000)
