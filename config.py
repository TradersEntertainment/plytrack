import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env or environment")

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 2))

# Optional Deployment Defaults
DEFAULT_CHAT_ID = os.getenv("DEFAULT_CHAT_ID")
DEFAULT_WALLET = os.getenv("DEFAULT_WALLET")

# Web Dashboard Settings
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")
PORT = int(os.getenv("PORT", 8080)) # Railway provides PORT automatically
