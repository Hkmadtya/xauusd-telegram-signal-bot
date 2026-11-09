
import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "XAUUSD Signal Bot berhasil terhubung! ✅\n"
        "Ketik /test untuk mencoba sinyal simulasi."
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "🧪 XAUUSD — SIMULASI SAJA\n\n"
        "📊 ARAH: BUY\n"
        "ENTRY: 2650.00\n"
        "STOP LOSS: 2645.00\n"
        "TP1: 2660.00\n"
        "TP2: 2665.00\n\n"
        "⚠️ Ini data contoh, bukan harga pasar "
        "dan bukan rekomendasi trading."
    )
    await update.message.reply_text(message)

@app.get("/")
def health():
    return "XAUUSD Telegram test bot is running", 200

def run_telegram():
    bot = Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("test", test))
    bot.run_polling(stop_signals=None)

if __name__ == "__main__":
    threading.Thread(target=run_telegram, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
