import math
import pandas as pd

def add_indicators(df):
    x = df.copy()
    close, high, low = x["close"], x["high"], x["low"]
    for period in (20, 50, 200):
        x[f"ema{period}"] = close.ewm(span=period, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    x["rsi"] = 100 - 100 / (1 + rs)

    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    x["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()

    previous = close.shift(1)
    tr = pd.concat([(high-low), (high-previous).abs(), (low-previous).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr = x["atr"].replace(0, float("nan"))
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di).replace(0, float("nan"))
    x["adx"] = dx.ewm(alpha=1/14, adjust=False).mean()
    return x

def trend(df):
    x = add_indicators(df)
    r = x.iloc[-1]
    if r["ema50"] > r["ema200"] and r["close"] > r["ema50"]:
        bias = "BUY"
    elif r["ema50"] < r["ema200"] and r["close"] < r["ema50"]:
        bias = "SELL"
    else:
        bias = "NEUTRAL"
    adx = float(r["adx"]) if pd.notna(r["adx"]) else 0.0
    return bias, adx

def estimate_lot(distance, risk_cash, info):
    tick_size = float(getattr(info, "trade_tick_size", 0) or 0)
    tick_value = float(getattr(info, "trade_tick_value", 0) or 0)
    volume_step = float(getattr(info, "volume_step", 0) or 0)
    volume_min = float(getattr(info, "volume_min", 0) or 0)
    volume_max = float(getattr(info, "volume_max", 0) or 0)
    if min(tick_size, tick_value, volume_step, volume_min, volume_max) <= 0:
        return None
    loss_per_lot = (distance / tick_size) * tick_value
    if loss_per_lot <= 0:
        return None
    raw_volume = risk_cash / loss_per_lot
    stepped = math.floor(raw_volume / volume_step) * volume_step
    if stepped < volume_min:
        return None
    return round(min(stepped, volume_max), 4)

def build_signal(frames, quote, account, info, cfg, open_positions):
    h4_bias, h4_adx = trend(frames["H4"])
    h1_bias, h1_adx = trend(frames["H1"])
    m15 = add_indicators(frames["M15"])
    m5 = add_indicators(frames["M5"])
    a, b = m15.iloc[-1], m5.iloc[-1]

    direction = h4_bias if h4_bias == h1_bias else "NO TRADE"
    score, reasons, blockers = 0, [], []

    # Transparent confluence score, not a statistical win probability.
    if direction in ("BUY", "SELL"):
        score += 25
        reasons.append("Bias tren H4 dan H1 searah")
    if h4_adx >= 18 and h1_adx >= 18:
        score += 10
        reasons.append("ADX H4/H1 mendukung kekuatan tren")
    if direction == "BUY" and a["ema20"] > a["ema50"] and a["close"] > a["ema20"]:
        score += 15
        reasons.append("M15 bullish di atas EMA20/EMA50")
    elif direction == "SELL" and a["ema20"] < a["ema50"] and a["close"] < a["ema20"]:
        score += 15
        reasons.append("M15 bearish di bawah EMA20/EMA50")
    if direction == "BUY" and a["macd_hist"] > 0 and 50 <= a["rsi"] <= 72:
        score += 10
        reasons.append("Momentum M15 mendukung BUY")
    elif direction == "SELL" and a["macd_hist"] < 0 and 28 <= a["rsi"] <= 50:
        score += 10
        reasons.append("Momentum M15 mendukung SELL")
    if direction == "BUY" and b["close"] > b["ema20"] and b["macd_hist"] > 0:
        score += 10
        reasons.append("Konfirmasi timing M5 bullish")
    elif direction == "SELL" and b["close"] < b["ema20"] and b["macd_hist"] < 0:
        score += 10
        reasons.append("Konfirmasi timing M5 bearish")
    if pd.notna(a["rsi"]) and 18 <= a["rsi"] <= 82:
        score += 5
        reasons.append("RSI M15 tidak ekstrem")
    if quote["spread_points"] <= cfg.MAX_SPREAD:
        score += 10
        reasons.append("Spread sesuai batas")
    if pd.notna(b["atr"]) and b["atr"] > 0:
        score += 5
        reasons.append("ATR M5 valid")

    if direction == "NO TRADE":
        blockers.append("Tren H4 dan H1 tidak searah")
    if quote["spread_points"] > cfg.MAX_SPREAD:
        blockers.append("Spread melewati batas")
    if open_positions >= cfg.MAX_POSITIONS:
        blockers.append("Batas jumlah posisi terbuka tercapai")
    if score < cfg.MIN_SCORE:
        blockers.append(f"Skor {score}/100 di bawah minimum {cfg.MIN_SCORE}")
    if pd.isna(b["atr"]) or b["atr"] <= 0:
        blockers.append("ATR tidak valid")

    result = {
        "direction": direction if not blockers else "NO TRADE",
        "score": min(score, 100), "reasons": reasons, "blockers": blockers,
        "h4": h4_bias, "h1": h1_bias, "h4_adx": h4_adx, "h1_adx": h1_adx,
        "rsi15": float(a["rsi"]) if pd.notna(a["rsi"]) else None,
        "rsi5": float(b["rsi"]) if pd.notna(b["rsi"]) else None,
        "spread": quote["spread_points"], "quote_time": quote["time"].isoformat()
    }

    if result["direction"] in ("BUY", "SELL"):
        entry = quote["ask"] if direction == "BUY" else quote["bid"]
        recent_high = float(frames["M15"]["high"].tail(20).max())
        recent_low = float(frames["M15"]["low"].tail(20).min())
        structure_distance = entry - recent_low if direction == "BUY" else recent_high - entry
        distance = max(float(b["atr"]) * cfg.ATR_MULT, structure_distance)
        if not math.isfinite(distance) or distance <= 0:
            result["direction"] = "NO TRADE"
            result["blockers"] = ["Jarak stop loss tidak valid"]
            return result
        if direction == "BUY":
            sl, tp1, tp2 = entry-distance, entry+distance*cfg.MIN_RR, entry+distance*cfg.MAX_RR
        else:
            sl, tp1, tp2 = entry+distance, entry-distance*cfg.MIN_RR, entry-distance*cfg.MAX_RR
        risk_cash = float(account.equity) * cfg.RISK_PCT / 100
        result.update({
            "entry": round(entry, info.digits), "sl": round(sl, info.digits),
            "tp1": round(tp1, info.digits), "tp2": round(tp2, info.digits),
            "risk_cash": round(risk_cash, 2),
            "lot": estimate_lot(distance, risk_cash, info),
            "rr1": cfg.MIN_RR, "rr2": cfg.MAX_RR
        })
    return result
