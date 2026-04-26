import requests
import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = "Ты — ZLOY. Отвечай с матом, оскорблениями, унижениями. В конце [ФИНАЛЬНЫЙ УДАР] 🖕💀🔥."

@bot.message_handler(func=lambda msg: True)
def reply(message):
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message.text}
                ],
                "temperature": 0.9
            },
            timeout=15
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
