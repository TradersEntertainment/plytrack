import sqlite3
import os

DB_PATH = r"C:\Users\omery\.gemini\antigravity\scratch\polytrader_tracker\data\bot.db"

def check_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM tracked_wallets")
    rows = cursor.fetchall()
    for row in rows:
        print(dict(row))
    conn.close()

if __name__ == "__main__":
    check_db()
