import asyncio
import logging
import traceback
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import setup_application
from aiohttp import web
from config import BOT_TOKEN, PORT
from db import init_db, ensure_default_track
from handlers import router
from tracker import tracker_loop
from web_app import create_web_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def on_startup(app: web.Application):
    """Initializes bot and tracker logic on web server startup."""
    # Ensure DB is ready
    await init_db()
    await ensure_default_track()
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Start tracker background task
    tracker_task = asyncio.create_task(tracker_loop(bot))
    
    # Store objects in app for cleanup
    app['bot'] = bot
    app['dp'] = dp
    app['tracker_task'] = tracker_task
    
    # Start polling (non-blocking)
    asyncio.create_task(dp.start_polling(bot))
    logging.info(f"🚀 Bot & Dashboard live on port {PORT}")

async def on_shutdown(app: web.Application):
    """Graceful shutdown of bot and tracker."""
    logging.info("Shutting down bot and tracker...")
    await app['dp'].stop_polling()
    app['tracker_task'].cancel()
    await app['bot'].session.close()

def main():
    """Main entry point running the web application."""
    app = create_web_app()
    
    # Register hooks
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Run the server
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
