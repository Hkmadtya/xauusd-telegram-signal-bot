# XAUUSD Telegram Signal-Only Bot — MT5 Hybrid

## Scope
- Instrumen: XAUUSD (Gold)
- Data source: local MetaTrader 5 terminal
- Style: Hybrid (H4/H1 trend, M15 setup, M5 timing)
- Risk profile: medium; nominal risk estimate 1% equity per setup
- Telegram delivery: private chat
- Automatic scan: every 15 minutes
- Execution: signal only. No trade/order functions exist in this project.

## Requirements and important compatibility
MetaTrader5 Python package is intended for Windows. Run this on Windows 10/11
or a Windows VPS with MT5 desktop installed and logged in. It will not run
directly on an iPhone. Linux VPS requires a different MT5 bridge/data architecture.

## Setup
1. Install 64-bit Python 3.11+ and MetaTrader 5 desktop on Windows.
2. Log in to your broker account in MT5 and show the gold symbol in Market Watch.
3. Create a Telegram bot with @BotFather and obtain the token.
4. Obtain your numeric Telegram user/chat ID.
5. Copy `.env.example` to `.env`.
6. Fill `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ADMIN_USER_IDS`.
7. Set `MT5_SYMBOL` to the exact broker symbol shown in Market Watch. "Lainnya"
   is not a usable symbol name; it may be XAUUSD, XAUUSDm, GOLD, GOLD.pro, etc.

PowerShell:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Open the bot's private chat and send `/start`. Use `/signal` for an immediate
analysis. Scheduled scans run every 15 minutes and only send BUY/SELL alerts
that pass the score, spread, position-count and cooldown gates. The bot sends
a NO TRADE response when manually requested but does not spam scheduled NO TRADE messages.

## Telegram commands
/start, /help, /signal, /price, /status, /analysis, /trend, /performance,
/pause, /resume. Pause/resume are restricted to configured admin IDs.

## Strategy
- H4/H1 EMA50 and EMA200 directional bias.
- M15 EMA20/EMA50, RSI and MACD histogram confirmation.
- M5 momentum timing and ATR-based stop distance.
- Weighted confluence score; score is not a win probability.
- SL distance uses max(1.5 x M5 ATR, recent 20-candle M15 structure distance).
- TP1 = 2R; TP2 = 3R.
- Estimated lot uses MT5 tick size/value and volume constraints.
- Current, unfinished candles are excluded.

## Safety / limitations — read before use
This is an initial working reference implementation, not a validated profitable
trading system and not financial advice. Test on demo and inspect signals manually.
Broker-specific spread, tick value, contract size, execution, commission and slippage
can materially change results. Lot is an estimate, not a guaranteed loss cap.

The news pause is manual only; this package does not include an economic calendar
feed. Keep the manual news pause policy in place and do not rely on alerts around
CPI, PCE, NFP, FOMC or other high-impact events. Daily drawdown baseline in this
starter is initialized at process startup and resets after restart; persist the
baseline before production deployment. It uses the MT5 account's current open
positions count as a conservative guard, but it does not know which positions
were opened by this signal bot.

Before live use, add and validate: persistent daily equity baseline, news calendar
integration, backtesting with tick data and realistic costs, outcome tracking,
monitoring, and a broker-specific risk sizing verification. The bot does not
execute trades and contains no order_send calls.
