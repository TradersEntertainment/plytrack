import aiohttp
import asyncio
from datetime import datetime, timezone
import collections

USER_ADDRESS = "0x5fe14b52584c83c18496914db0b30a28d4510981"
API_URL = f"https://data-api.polymarket.com/activity?user={USER_ADDRESS}&limit=500"

async def analyze_activity():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, headers=headers) as resp:
            if resp.status != 200:
                print(f"Error fetching data: {resp.status}")
                return
            
            data = await resp.json()
            
            trades = [item for item in data if item.get("type") == "TRADE"]
            if not trades:
                print("No trades found to analyze.")
                return
            
            # Hours in UTC (0-23)
            hour_counts = collections.Counter()
            
            for trade in trades:
                ts = trade.get("timestamp")
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                hour_counts[dt.hour] += 1
            
            print(f"\n--- {USER_ADDRESS} (Bitara) Activity Analysis ---")
            print(f"Analyzed {len(trades)} trades over the recent period.\n")
            
            print("Hour (UTC) | Trade Count")
            print("-----------|------------")
            for h in range(24):
                count = hour_counts.get(h, 0)
                bar = "#" * (count // 2) if count > 0 else ""
                print(f"{h:02d}:00      | {count:3} {bar}")
            
            inactive_hours = [h for h in range(24) if hour_counts.get(h, 0) < 5] # Less than 5 trades in recent history
            print(f"\nPotential Inactive Hours (UTC): {inactive_hours}")

if __name__ == "__main__":
    asyncio.run(analyze_activity())
