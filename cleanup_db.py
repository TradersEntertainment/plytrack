import sqlite3
import os

DB_PATH = r"C:\Users\omery\.gemini\antigravity\scratch\polytrader_tracker\data\bot.db"
OLD_CHAT_ID = -1003935870650

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tracked_wallets WHERE user_id = ?", (OLD_CHAT_ID,))
    cursor.execute("DELETE FROM users WHERE user_id = ?", (OLD_CHAT_ID,))
    conn.commit()
    print(f"Cleaned up old chat ID {OLD_CHAT_ID}")
    conn.close()

if __name__ == "__main__":
    cleanup()
