import asyncio
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import MetaTrader5 as mt5

from config import cfg, validate
from mt5_feed import MT5Feed
from analysis_engine import build_signal
from database import init_db, is_duplicate, save_signal, totals

feed = MT5Feed(cfg)
paused = False
day_start_equity = None
day_key = None
daily_locked = False

def check_daily_drawdown(account):
    global day_start_equity, day_key, daily_locked
    today = datetime.now(timezone.utc).date().isoformat()
    if day_key != today:
        day_key = today
        day_start_equity = float(account.equity)
        daily_locked = False
    if day_start_equity and day_start_equity > 0:
        dd = (day_start_equity - float(account.equity)) / day_start_equity * 100
        if dd >= cfg.MAX_DAILY_DD_PCT:
            daily_locked = True
    return daily_locked

async def analyze_now():
    def worker():
        quote = feed.quote()
        frames = feed.all_frames()
        account = feed.account()
        if check_daily_drawdown(account):
            return {"direction": "NO TRADE", "score": 0, "h4": "-", "h1": "-",
                    "spread": quote["spread_points"],
                    "blockers": [f"Daily drawdown guard {cfg.MAX_DAILY_DD_PCT}% aktif; alert BUY/SELL dihentikan sampai hari UTC berikutnya."],
                    "reasons": []}
        return build_signal(frames, quote, account, feed.symbol_info(), cfg,
                            feed.open_positions_count())
    return await asyncio.to_thread(worker)

def format_signal(s):
    if s["direction"] == "NO TRADE":
        blockers = s.get("blockers") or ["Belum ada setup yang memenuhi syarat"]
        return (f"🥇 {cfg.SYMBOL} — NO TRADE\n"
                f"Score: {s.get('score', 0)}/100\n"
                f"H4: {s.get('h4', '-')} | H1: {s.get('h1', '-')}\n"
                f"Spread: {s.get('spread', 0):.1f} points\n\nAlasan:\n- "
                + "\n- ".join(blockers))
    lot = str(s["lot"]) if s.get("lot") is not None else "Tidak dapat dihitung; periksa contract/tick value broker"
    return (
        f"🥇 {cfg.SYMBOL} SIGNAL\n"
        f"📊 ARAH: {s['direction']}\n"
        f"⭐ SETUP: {'STRONG' if s['score'] >= 80 else 'VALID'}\n"
        f"Skor konfluensi: {s['score']}/100 (bukan probabilitas menang)\n\n"
        f"ENTRY: {s['entry']}\nSTOP LOSS: {s['sl']}\n"
        f"TP1: {s['tp1']} (RR 1:{s['rr1']})\nTP2: {s['tp2']} (RR 1:{s['rr2']})\n"
        f"Estimasi lot pada risiko {cfg.RISK_PCT}%: {lot}\n"
        f"Spread: {s['spread']:.1f} points\n"
        f"H4/H1: {s['h4']} / {s['h1']}\n"
        f"RSI M15/M5: {s['rsi15']:.1f} / {s['rsi5']:.1f}\n\n"
        "ANALISIS:\n- " + "\n- ".join(s["reasons"]) +
        "\n\nMode SIGNAL ONLY. Bot tidak membuka, mengubah, atau menutup posisi."
    )

def is_admin(update):
    return update.effective_user and update.effective_user.id in cfg.ADMINS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "XAUUSD Hybrid Signal Bot aktif.\n"
        "Data: MT5 | Pemeriksaan: setiap 15 menit | Risk: Medium (1%)\n"
        "Gunakan /signal /price /status /analysis /trend /performance /help."
    )

async def help_cmd(update, context):
    await update.message.reply_text(
        "/signal — analisis dan sinyal terbaru\n/price — bid/ask dan spread\n"
        "/status — koneksi MT5 dan status alert\n/analysis — ringkasan multi-timeframe\n"
        "/trend — bias H4/H1\n/performance — jumlah sinyal tersimpan\n"
        "/pause dan /resume — jeda/aktifkan alert otomatis (admin)"
    )

async def signal_cmd(update, context):
    try:
        s = await analyze_now()
        await update.message.reply_text(format_signal(s))
    except Exception as e:
        await update.message.reply_text(f"Analisis gagal; tidak ada sinyal yang dikirim. Detail: {e}")

async def price_cmd(update, context):
    try:
        q = await asyncio.to_thread(feed.quote)
        await update.message.reply_text(
            f"{cfg.SYMBOL}\nBid: {q['bid']}\nAsk: {q['ask']}\n"
            f"Spread: {q['spread_points']:.1f} points\nQuote UTC: {q['time'].isoformat()}"
        )
    except Exception as e:
        await update.message.reply_text(f"Quote MT5 tidak tersedia: {e}")

async def status_cmd(update, context):
    try:
        q = await asyncio.to_thread(feed.quote)
        await update.message.reply_text(
            f"MT5: CONNECTED\nSymbol: {cfg.SYMBOL}\n"
            f"Bid/Ask: {q['bid']} / {q['ask']}\nSpread: {q['spread_points']:.1f}\n"
            f"Alert otomatis: {'PAUSED' if paused else 'ACTIVE'}"
        )
    except Exception as e:
        await update.message.reply_text(f"MT5: DISCONNECTED\n{e}")

async def analysis_cmd(update, context):
    try:
        s = await analyze_now()
        await update.message.reply_text(format_signal(s))
    except Exception as e:
        await update.message.reply_text(f"Analisis gagal: {e}")

async def trend_cmd(update, context):
    try:
        s = await analyze_now()
        await update.message.reply_text(f"Tren XAUUSD\nH4: {s.get('h4','-')}\nH1: {s.get('h1','-')}\nKeputusan: {s['direction']}\nSkor: {s['score']}/100")
    except Exception as e:
        await update.message.reply_text(f"Data tren tidak tersedia: {e}")

async def performance_cmd(update, context):
    await update.message.reply_text(
        f"Total alert tersimpan: {totals()}\n"
        "Hasil menang/kalah belum dihitung otomatis. Angka ini bukan performa profit."
    )

async def pause_cmd(update, context):
    global paused
    if not is_admin(update):
        return await update.message.reply_text("Perintah khusus admin.")
    paused = True
    await update.message.reply_text("Alert otomatis dijeda. Perintah /signal manual tetap tersedia.")

async def resume_cmd(update, context):
    global paused
    if not is_admin(update):
        return await update.message.reply_text("Perintah khusus admin.")
    paused = False
    await update.message.reply_text("Alert otomatis diaktifkan.")

async def scheduled_scan(context: ContextTypes.DEFAULT_TYPE):
    if paused:
        return
    try:
        s = await analyze_now()
        if s["direction"] in ("BUY", "SELL"):
            if not is_duplicate(s["direction"], s["score"], cfg.COOLDOWN_MINUTES):
                save_signal(s)
                await context.bot.send_message(chat_id=cfg.CHAT_ID, text=format_signal(s))
    except Exception as e:
        await context.bot.send_message(
            chat_id=cfg.CHAT_ID,
            text=f"⚠️ Bot tidak dapat memvalidasi data MT5. Tidak ada sinyal dikirim.\n{e}"
        )

def main():
    global day_start_equity, day_key
    validate()
    init_db()
    feed.connect()
    # Establish daily equity baseline at process start. Restarting the bot resets
    # this baseline; production deployments should persist the baseline in SQLite.
    account = feed.account()
    day_start_equity = float(account.equity)
    day_key = datetime.now(timezone.utc).date().isoformat()

    app = Application.builder().token(cfg.TOKEN).build()
    handlers = [
        ("start", start), ("help", help_cmd), ("signal", signal_cmd),
        ("price", price_cmd), ("status", status_cmd), ("analysis", analysis_cmd),
        ("trend", trend_cmd), ("performance", performance_cmd),
        ("pause", pause_cmd), ("resume", resume_cmd)
    ]
    for name, callback in handlers:
        app.add_handler(CommandHandler(name, callback))
    app.job_queue.run_repeating(
        scheduled_scan, interval=cfg.INTERVAL_MINUTES * 60, first=20
    )
    try:
        app.run_polling()
    finally:
        feed.shutdown()

if __name__ == "__main__":
    main()
