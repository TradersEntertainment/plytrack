import asyncio
import aiosqlite
import os

DB_PATH = r"C:\Users\omery\.gemini\antigravity\scratch\polytrader_tracker\data\bot.db"
NEW_CHAT_ID = -5250517474
ADDRESS = "0x5fe14b52584c83c18496914db0b30a28d4510981"

async def update_chat_id():
    async with aiosqlite.connect(DB_PATH) as db:
        # Add new user
        await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (NEW_CHAT_ID,))
        # Link address to new user
        await db.execute(
            'INSERT OR IGNORE INTO tracked_wallets (user_id, address) VALUES (?, ?)',
            (NEW_CHAT_ID, ADDRESS.lower())
        )
        await db.commit()
    print(f"Added {ADDRESS} for new chat {NEW_CHAT_ID}")

if __name__ == "__main__":
    asyncio.run(update_chat_id())
