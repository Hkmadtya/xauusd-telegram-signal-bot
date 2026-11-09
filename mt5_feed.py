from datetime import datetime, timezone
import MetaTrader5 as mt5
import pandas as pd

TIMEFRAMES = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
}

class MT5Feed:
    def __init__(self, cfg):
        self.cfg = cfg
        self.connected = False

    def connect(self):
        args = {}
        if self.cfg.MT5_PATH:
            args["path"] = self.cfg.MT5_PATH
        if self.cfg.MT5_LOGIN and self.cfg.MT5_PASSWORD and self.cfg.MT5_SERVER:
            args.update(login=int(self.cfg.MT5_LOGIN),
                        password=self.cfg.MT5_PASSWORD, server=self.cfg.MT5_SERVER)
        if not mt5.initialize(**args):
            raise RuntimeError(f"MT5 initialize gagal: {mt5.last_error()}")
        if not mt5.symbol_select(self.cfg.SYMBOL, True):
            raise RuntimeError(
                f"Simbol '{self.cfg.SYMBOL}' tidak ditemukan. Periksa nama simbol broker di Market Watch."
            )
        self.connected = True

    def ensure(self):
        if not self.connected or mt5.terminal_info() is None:
            self.connect()

    def quote(self):
        self.ensure()
        tick = mt5.symbol_info_tick(self.cfg.SYMBOL)
        info = mt5.symbol_info(self.cfg.SYMBOL)
        if tick is None or info is None or tick.bid <= 0 or tick.ask <= 0:
            raise RuntimeError(f"Quote MT5 tidak valid: {mt5.last_error()}")
        return {
            "bid": float(tick.bid), "ask": float(tick.ask),
            "spread_points": float((tick.ask - tick.bid) / info.point),
            "point": float(info.point), "digits": int(info.digits),
            "time": datetime.fromtimestamp(tick.time, timezone.utc)
        }

    def candles(self, tf, count=350):
        self.ensure()
        rates = mt5.copy_rates_from_pos(self.cfg.SYMBOL, TIMEFRAMES[tf], 0, count)
        if rates is None or len(rates) < 220:
            raise RuntimeError(f"Data candle {tf} tidak cukup: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        # Ignore still-forming candle to prevent repaint-like changes.
        return df.iloc[:-1].reset_index(drop=True)

    def all_frames(self):
        return {tf: self.candles(tf) for tf in ("H4", "H1", "M15", "M5")}

    def account(self):
        self.ensure()
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("Informasi akun MT5 tidak tersedia")
        return account

    def symbol_info(self):
        self.ensure()
        info = mt5.symbol_info(self.cfg.SYMBOL)
        if info is None:
            raise RuntimeError("Spesifikasi simbol tidak tersedia")
        return info

    def open_positions_count(self):
        self.ensure()
        positions = mt5.positions_get(symbol=self.cfg.SYMBOL)
        return len(positions) if positions else 0

    def shutdown(self):
        mt5.shutdown()
        self.connected = False
