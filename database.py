import sqlite3
from datetime import datetime, timezone, timedelta

DB = "signal_history.sqlite3"

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, direction TEXT NOT NULL,
            score INTEGER NOT NULL, entry REAL, sl REAL, tp1 REAL,
            status TEXT NOT NULL DEFAULT 'UNVERIFIED'
        )''')

def is_duplicate(direction, score, cooldown_minutes):
    cutoff = (datetime.now(timezone.utc)-timedelta(minutes=cooldown_minutes)).isoformat()
    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT 1 FROM signals WHERE created_at >= ? AND direction = ? AND score >= ? LIMIT 1",
            (cutoff, direction, score-5)
        ).fetchone()
    return row is not None

def save_signal(s):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO signals(created_at,direction,score,entry,sl,tp1) VALUES(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), s["direction"], s["score"],
             s.get("entry"), s.get("sl"), s.get("tp1"))
        )

def totals():
    with sqlite3.connect(DB) as con:
        return con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
