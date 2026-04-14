import os
import json
import logging
from aiohttp import web
import aiohttp_jinja2
import jinja2
from config import WEB_PASSWORD, PORT, DB_PATH
from db import get_tracked_wallets, add_tracked_wallet, remove_tracked_wallet

logger = logging.getLogger(__name__)

async def check_auth(request):
    """Simple password check via query param or session for now."""
    passed_pw = request.query.get("pw")
    if passed_pw != WEB_PASSWORD:
        return False
    return True

async def index(request):
    if not await check_auth(request):
        return web.Response(text="Unauthorized. Access denied.", status=401)
    
    # Serve the HTML dashboard
    # For now, we'll keep it simple and serve a single HTML file
    return web.FileResponse('templates/dashboard.html')

async def api_get_wallets(request):
    if not await check_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    
    wallets = await get_tracked_wallets()
    return web.json_response({"wallets": wallets})

async def api_track(request):
    if not await check_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    
    data = await request.json()
    address = data.get("address")
    chat_id = data.get("chat_id")
    
    if not address or not chat_id:
        return web.json_response({"error": "missing data"}, status=400)
    
    try:
        success = await add_tracked_wallet(int(chat_id), address)
        return web.json_response({"success": success})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_untrack(request):
    if not await check_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    
    data = await request.json()
    address = data.get("address")
    chat_id = data.get("chat_id")
    
    if not address or not chat_id:
        return web.json_response({"error": "missing data"}, status=400)
    
    success = await remove_tracked_wallet(int(chat_id), address)
    return web.json_response({"success": success})

def create_web_app():
    app = web.Application()
    
    # Routes
    app.router.add_get('/', index)
    app.router.add_get('/api/wallets', api_get_wallets)
    app.router.add_post('/api/track', api_track)
    app.router.add_post('/api/untrack', api_untrack)
    
    return app
