import asyncio
import aiosqlite
import os

DB_PATH = r"C:\Users\omery\.gemini\antigravity\scratch\polytrader_tracker\data\bot.db"
CHAT_ID = -1003935870650
ADDRESS = "0x5fe14b52584c83c18496914db0b30a28d4510981"

async def add_target():
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (CHAT_ID,))
        await db.execute(
            'INSERT OR IGNORE INTO tracked_wallets (user_id, address) VALUES (?, ?)',
            (CHAT_ID, ADDRESS.lower())
        )
        await db.commit()
    print(f"Added {ADDRESS} for chat {CHAT_ID}")

if __name__ == "__main__":
    asyncio.run(add_target())
