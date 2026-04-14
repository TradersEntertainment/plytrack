import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env or environment")

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 15))
