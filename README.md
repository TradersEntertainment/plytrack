# Polytrader Tracker 🚀

High-speed Polymarket transaction tracking bot for Telegram.

## Features
- **Real-time Monitoring:** Uses the `/activity` endpoint for faster trade detection (~8 minutes ahead of standard trade lists).
- **Self-Healing:** Infinite loop wrapper with auto-restart logic ensuring 24/7 uptime even after crashes.
- **Robust Deduplication:** Uses a local SQLite history to track up to 500 transactions per wallet, preventing duplicate alerts across restarts.
- **Mobile-First Design:** Notifications optimized for phone lock-screens with clear emojis and price data.

## Deployment (Railway)
1. **GitHub:** Push this code to your repository.
2. **Railway:** Create a new project from your GitHub repo.
3. **Environment Variables:** Set the following variables in Railway:
   - `BOT_TOKEN`: Your Telegram Bot Token.
   - `POLL_INTERVAL`: 5
   - `DB_PATH`: `data/bot.db`
   - `DEFAULT_CHAT_ID`: Your group Chat ID (e.g., `-100...`).
   - `DEFAULT_WALLET`: The wallet address to track by default.
4. **Volumes (Persistent Data):** 
   - Since SQLite is used, adding a Railway Volume mounted at `/app/data` is recommended to keep tracked wallets across deployments.

## Commands
- `/start` - Start the bot
- `/track <address>` - Follow a wallet
- `/untrack <address>` - Stop following
- `/list` - List active tracks
