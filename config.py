import os
from dotenv import load_dotenv

load_dotenv()

def env_int(name, default):
    return int(os.getenv(name, str(default)))

def env_float(name, default):
    return float(os.getenv(name, str(default)))

class Config:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    ADMINS = {int(x.strip()) for x in os.getenv("ADMIN_USER_IDS", "").split(",")
              if x.strip().isdigit()}
    MT5_PATH = os.getenv("MT5_PATH", "").strip()
    MT5_LOGIN = os.getenv("MT5_LOGIN", "").strip()
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "").strip()
    SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD").strip()
    INTERVAL_MINUTES = env_int("SCAN_INTERVAL_MINUTES", 15)
    MIN_SCORE = env_int("MIN_SIGNAL_SCORE", 70)
    RISK_PCT = env_float("RISK_PER_TRADE_PCT", 1.0)
    MAX_DAILY_DD_PCT = env_float("MAX_DAILY_DRAWDOWN_PCT", 3.0)
    MAX_SPREAD = env_float("MAX_SPREAD_POINTS", 100)
    MAX_POSITIONS = env_int("MAX_OPEN_POSITIONS", 3)
    COOLDOWN_MINUTES = env_int("SIGNAL_COOLDOWN_MINUTES", 60)
    ATR_MULT = env_float("ATR_SL_MULTIPLIER", 1.5)
    MIN_RR = env_float("MIN_RR", 2.0)
    MAX_RR = env_float("MAX_RR", 3.0)
    MANUAL_NEWS_PAUSE = os.getenv("MANUAL_NEWS_PAUSE", "true").lower() == "true"

cfg = Config()

def validate():
    if not cfg.TOKEN or not cfg.CHAT_ID:
        raise RuntimeError("Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di .env")
    if cfg.INTERVAL_MINUTES < 1:
        raise RuntimeError("SCAN_INTERVAL_MINUTES minimal 1")
    if not 0 < cfg.RISK_PCT <= 1.5:
        raise RuntimeError("RISK_PER_TRADE_PCT harus > 0 dan <= 1.5")
    if cfg.MIN_RR < 2 or cfg.MAX_RR < cfg.MIN_RR:
        raise RuntimeError("Pastikan MIN_RR >= 2 dan MAX_RR >= MIN_RR")
    if cfg.MIN_SCORE < 1 or cfg.MIN_SCORE > 100:
        raise RuntimeError("MIN_SIGNAL_SCORE harus 1 sampai 100")
