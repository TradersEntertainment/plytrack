import asyncio
import aiohttp
import logging
from aiogram import Bot
from db import get_tracked_wallets, update_last_seen, is_activity_seen, record_activity
from config import POLL_INTERVAL

logger = logging.getLogger(__name__)

POLYMARKET_API_URL = "https://data-api.polymarket.com/activity"

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
    """Fetch trades for a specific wallet from Polymarket Data API with cache busting."""
    import time
    params = {
        "user": address, 
        "limit": 20,
        "ts": int(time.time()) # Cache breaker
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with session.get(POLYMARKET_API_URL, params=params, headers=headers) as response:
            logger.info(f"API Request to {address} returned status {response.status}")
            if response.status == 200:
                data = await response.json()
                # Filter out ONLY trades (ignore REDEEM, etc. unless desired)
                trades = [item for item in data if item.get("type") == "TRADE"]
                logger.info(f"API Activity for {address}: {len(data)} total, {len(trades)} trades")
                return trades
            else:
                logger.error(f"Error fetching activity for {address}: HTTP {response.status}")
                return None
    except Exception as e:
        logger.error(f"Exception fetching trades for {address}: {e}")
        return None

async def tracker_loop(bot: Bot):
    """Background loop to check for new trades."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                wallets = await get_tracked_wallets()
                if not wallets:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                for record in wallets:
                    try:
                        user_id = record['user_id']
                        address = record['address']
                        last_seen_id = record.get('last_seen_trade_id')

                        logger.info(f"Checking {address} (Chat: {user_id}), Last Seen: {last_seen_id}")
                        trades = await fetch_recent_trades(session, address)
                        if not trades:
                            continue
                        
                        # Use activity_history to find truly new trades
                        new_trades = []
                        for i, trade in enumerate(trades):
                            trade_id = trade.get("transactionHash")
                            if i == 0:
                                logger.info(f"Latest trade in API for {address}: {trade_id}")
                            
                            if await is_activity_seen(address, trade_id):
                                break
                            new_trades.append(trade)
                        
                        if new_trades:
                            logger.info(f"Detected {len(new_trades)} new trades for {address}")
                            # Process trades from oldest to newest
                            for trade in reversed(new_trades):
                                try:
                                    tx_hash = trade.get("transactionHash")
                                    msg = format_telegram_message(address, trade)
                                    await bot.send_message(user_id, msg, parse_mode="HTML")
                                    await record_activity(address, tx_hash, trade.get("timestamp"))
                                    logger.info(f"Alert sent to {user_id} for {address}")
                                except Exception as e:
                                    logger.error(f"Failed to send/format alert to {user_id}: {e}")
                            
                            # Update last seen for legacy support/UI
                            latest_trade = new_trades[0]
                            latest_hash = latest_trade.get("transactionHash")
                            latest_ts = latest_trade.get("timestamp")
                            await update_last_seen(user_id, address, latest_hash, latest_ts)
                            logger.info(f"Updated DB for {address} (Chat: {user_id}) to {latest_hash}")
                        else:
                            logger.info(f"No new trades for {address} (Chat: {user_id})")
                    except Exception as e:
                        logger.error(f"Critical error in wallet processing for {record.get('address')}: {e}")
                    
                    # Sleep slightly between different wallets to avoid bursts
                    await asyncio.sleep(0.5)
                
                # Main polling interval
                await asyncio.sleep(POLL_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                import traceback
                logger.error(f"Critical error in tracker loop: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(POLL_INTERVAL)
