import aiohttp
import asyncio
from datetime import datetime, timezone
import collections
import time

USER_ADDRESS = "0x5fe14b52584c83c18496914db0b30a28d4510981"
BASE_URL = "https://data-api.polymarket.com/activity"

async def fetch_page(session, offset, limit=500):
    url = f"{BASE_URL}?user={USER_ADDRESS}&limit={limit}&offset={offset}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with session.get(url, headers=headers) as resp:
        if resp.status == 200:
            return await resp.json()
        return []

async def analyze_long_term():
    async with aiohttp.ClientSession() as session:
        all_activities = []
        for offset in [0, 500, 1000, 1500, 2000]: # Fetch last 2500 entries
            print(f"Fetching offset {offset}...")
            data = await fetch_page(session, offset)
            if not data:
                break
            all_activities.extend(data)
            await asyncio.sleep(1) # Be nice to API
            
        trades = [item for item in all_activities if item.get("type") == "TRADE"]
        if not trades:
            print("No trades found.")
            return
            
        # Group by day and hour
        # Format: (Date, Hour)
        daily_hour_activity = collections.defaultdict(int)
        hourly_totals = collections.Counter()
        
        first_ts = trades[-1].get("timestamp")
        last_ts = trades[0].get("timestamp")
        first_date = datetime.fromtimestamp(first_ts, tz=timezone.utc)
        last_date = datetime.fromtimestamp(last_ts, tz=timezone.utc)
        
        for trade in trades:
            ts = trade.get("timestamp")
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            daily_hour_activity[(dt.date(), dt.hour)] += 1
            hourly_totals[dt.hour] += 1
            
        print(f"\n--- Bitara Long-Term Activity Analysis ---")
        print(f"Time Range: {first_date} to {last_date} (UTC)")
        print(f"Total Trades Analyzed: {len(trades)}\n")
        
        print("Hour (UTC) | Avg Trades/Hour | Heatmap (Recent Days)")
        print("-----------|-----------------|----------------------")
        
        # Get unique dates in order
        dates = sorted(list(set(d for d, h in daily_hour_activity.keys())), reverse=True)
        
        for h in range(24):
            total = hourly_totals.get(h, 0)
            avg = total / len(dates) if dates else 0
            
            # Create a small heatmap for the last few days
            heatmap = ""
            for d in dates[:5]: # Last 5 days
                count = daily_hour_activity.get((d, h), 0)
                if count > 50: heatmap += "[X]" # Very Active
                elif count > 10: heatmap += "[O]" # Active
                elif count > 0: heatmap += "[.]" # Low Activity
                else: heatmap += "[ ]" # Inactive
            
            print(f"{h:02d}:00      | {avg:6.1f}          | {heatmap}")

        print("\nHeatmap Key: [X] >50 | [O] >10 | [.] >0 | [ ] Inactive")
        print("Last 5 days (Left to Right: Newest to Oldest)")

if __name__ == "__main__":
    asyncio.run(analyze_long_term())
