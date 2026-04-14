import asyncio
import time
import aiohttp
import logging
from aiogram import Bot
from db import get_tracked_wallets, update_last_seen, is_activity_seen, record_activity
from config import POLL_INTERVAL

logger = logging.getLogger(__name__)

POLYMARKET_API_URL = "https://data-api.polymarket.com/activity"

# Persistent headers - mimic real browser to avoid throttling
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache, no-store",
    "Pragma": "no-cache",
}

def format_telegram_message(wallet: str, trade: dict) -> str:
    """Format trade dictionary into a readable Telegram message for mobile users."""
    side = trade.get("side", "UNKNOWN").upper()
    size = float(trade.get("size", 0))
    price = float(trade.get("price", 0))
    title = trade.get("title", "Unknown Market")
    outcome = trade.get("outcome", "Unknown Outcome")
    
    total_spent = round(size * price, 2)
    
    # Emoji based on outcome (Up = Green, Down = Red)
    if outcome.lower() == "up":
        emoji = "🟢"
    elif outcome.lower() == "down":
        emoji = "🔴"
    else:
        emoji = "🔵" # Default/Other cases
    
    # Keep the full title but maybe clean it up slightly if it's too long
    # Usually format is "Market Title - Time/Duration"
    display_title = title
    if " - " in title:
        parts = title.split(" - ")
        # If the second part is just a date, maybe we can combine them nicely
        display_title = f"{parts[0]}\n⏰ {parts[1]}"
    
    # Notification-friendly format (Visible on lock screen)
    msg = f"{emoji} <b>{total_spent}$</b> | <b>{outcome}</b>\n"
    msg += f"📊 {display_title}\n"
    msg += f"💰 Fiyat: <b>{price:.3f}$</b>\n\n"
    msg += f"👤 <code>{wallet}</code>"
    
    return msg

async def fetch_recent_trades(session: aiohttp.ClientSession, address: str):
    """Fetch trades for a specific wallet from Polymarket Data API with aggressive cache busting."""
    params = {
        "user": address, 
        "limit": 20,
        "_": int(time.time() * 1000)  # Millisecond precision cache breaker
    }
    try:
        async with session.get(POLYMARKET_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # Filter out ONLY trades (ignore REDEEM, etc. unless desired)
                trades = [item for item in data if item.get("type") == "TRADE"]
                return trades
            else:
                logger.warning(f"API {address[:10]}...: HTTP {response.status}")
                return None
    except Exception as e:
        logger.error(f"Fetch error {address[:10]}...: {e}")
        return None

async def process_wallet(bot: Bot, session: aiohttp.ClientSession, record: dict):
    """Process a single wallet - check for new trades and send notifications."""
    user_id = record['user_id']
    address = record['address']
    
    trades = await fetch_recent_trades(session, address)
    if not trades:
        return
    
    # Use activity_history to find truly new trades
    new_trades = []
    for trade in trades:
        trade_id = trade.get("transactionHash")
        if await is_activity_seen(address, trade_id):
            break
        new_trades.append(trade)
    
    if not new_trades:
        return
    
    logger.info(f"⚡ {len(new_trades)} new trades for {address[:10]}...")
    
    # Process trades from oldest to newest
    for trade in reversed(new_trades):
        try:
            tx_hash = trade.get("transactionHash")
            msg = format_telegram_message(address, trade)
            await bot.send_message(user_id, msg, parse_mode="HTML")
            await record_activity(address, tx_hash, trade.get("timestamp"))
        except Exception as e:
            logger.error(f"Send error to {user_id}: {e}")
    
    # Update last seen for legacy support/UI
    latest_trade = new_trades[0]
    await update_last_seen(user_id, address, latest_trade.get("transactionHash"), latest_trade.get("timestamp"))

async def tracker_loop(bot: Bot):
    """Ultra-fast background loop - parallel wallet checks, minimal delay."""
    
    # TCP connector with keep-alive for faster repeated requests
    connector = aiohttp.TCPConnector(
        limit=20,              # Max concurrent connections
        keepalive_timeout=60,  # Reuse TCP connections for 60s
        enable_cleanup_closed=True,
    )
    
    # Timeout config - fail fast, don't wait forever
    timeout = aiohttp.ClientTimeout(total=8, connect=3)
    
    async with aiohttp.ClientSession(
        connector=connector, 
        timeout=timeout,
        headers=HEADERS
    ) as session:
        cycle = 0
        while True:
            try:
                wallets = await get_tracked_wallets()
                if not wallets:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                # 🔥 PARALLEL: Query ALL wallets at the same time
                tasks = [
                    process_wallet(bot, session, record)
                    for record in wallets
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log every 30 cycles (~1 minute) to reduce noise
                cycle += 1
                if cycle % 30 == 0:
                    logger.info(f"✅ Alive | {len(wallets)} wallets | cycle {cycle}")
                
                # 🔥 Tight polling - check every POLL_INTERVAL seconds
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                import traceback
                logger.error(f"Tracker error: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(POLL_INTERVAL)
