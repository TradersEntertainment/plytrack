import asyncio
import logging
import traceback
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
from handlers import router
from tracker import tracker_loop

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_bot():
    """Main bot execution logic."""
    try:
        # Initialize DB
        await init_db()
        
        # Initialize bot and dispatcher
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        
        # Include routers
        dp.include_router(router)
        
        # Start tracker task
        tracker_task = asyncio.create_task(tracker_loop(bot))
        
        logging.info("Bot components initialized. Starting polling...")
        
        # Auto-restart logic (internal reset after 6 hours)
        async def restart_timer():
            RESTART_HOURS = 6
            await asyncio.sleep(RESTART_HOURS * 3600)
            logging.info(f"Scheduled internal restart triggered. Resetting components...")
            await dp.stop_polling()
            tracker_task.cancel()
        
        asyncio.create_task(restart_timer())
        
        # Start polling
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error in run_bot: {e}")
        logging.error(traceback.format_exc())
        raise e

async def main():
    """Infinite self-healing wrapper."""
    while True:
        try:
            await run_bot()
        except (KeyboardInterrupt, SystemExit):
            logging.info("Bot manually stopped.")
            break
        except Exception as e:
            logging.error(f"Bot crashed! Attempting self-healing in 10 seconds... Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
