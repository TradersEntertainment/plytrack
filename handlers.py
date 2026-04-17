import re
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from db import add_tracked_wallet, remove_tracked_wallet, get_user_tracked_wallets

router = Router()

def extract_address(text: str) -> str:
    """Extracts a 0x address from a string or URL."""
    match = re.search(r'(0x[a-fA-F0-9]{40})', text)
    if match:
        return match.group(1).lower()
    return ""

@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_msg = (
        "Merhaba! Polytrader Tracker Botuna hoş geldin.\n\n"
        "Takip etmek istediğin Polymarket cüzdan adresini (veya profil linkini) ekleyerek "
        "kullanıcının işlemlerini (alım/satım) anlık olarak takip edebilirsin.\n\n"
        "<b>Komutlar:</b>\n"
        "/track &lt;adres_veya_link&gt; - Yeni bir cüzdan takip et\n"
        "/untrack &lt;adres_veya_link&gt; - Cüzdan takibini bırak\n"
        "/list - Takip ettiğin tüm cüzdanları gör\n"
        "/last - En son yakalanan işlemi göster"
    )
    await message.answer(welcome_msg, parse_mode="HTML")

@router.message(Command("track"))
async def cmd_track(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Lütfen bir adres veya profil linki girin.\nÖrnek: `/track 0x123...` veya `/track https://polymarket.com/profile/0x123...`", parse_mode="Markdown")
        return
    
    address = extract_address(args[1])
    if not address:
        await message.answer("Geçerli bir cüzdan adresi (0x...) bulunamadı.")
        return
        
    chat_id = message.chat.id
    success = await add_tracked_wallet(chat_id, address)
    if success:
        await message.answer(f"✅ `{address}` adresi başarıyla takip listesine eklendi. Yeni bir işlem yapıldığında bildirim alacaksınız.", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Bu adresi zaten takip ediyorsunuz.")

@router.message(Command("untrack"))
async def cmd_untrack(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Lütfen bir adres veya profil linki girin.\nÖrnek: `/untrack 0x123...`", parse_mode="Markdown")
        return
    
    address = extract_address(args[1])
    if not address:
        await message.answer("Geçerli bir cüzdan adresi (0x...) bulunamadı.")
        return
        
    chat_id = message.chat.id
    success = await remove_tracked_wallet(chat_id, address)
    if success:
        await message.answer(f"❌ `{address}` takipten çıkarıldı.", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Bu adres takip listenizde bulunmuyor.")

@router.message(Command("list"))
async def cmd_list(message: Message):
    chat_id = message.chat.id
    wallets = await get_user_tracked_wallets(chat_id)
    if not wallets:
        await message.answer("Henüz takip ettiğiniz bir cüzdan yok.")
        return
        
    msg = "<b>Takip Ettiğiniz Cüzdanlar:</b>\n"
    for w in wallets:
        if w['nickname']:
            msg += f"- <b>{w['nickname']}</b>: <code>{w['address']}</code>\n"
        else:
            msg += f"- <code>{w['address']}</code>\n"
    
    await message.answer(msg, parse_mode="HTML")

@router.message(Command("last"))
async def cmd_last(message: Message):
    import aiosqlite
    from config import DB_PATH
    from datetime import datetime
    
    chat_id = message.chat.id
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get the newest activity for any wallet tracked in this chat
        query = '''
            SELECT h.*, w.nickname FROM activity_history h
            JOIN tracked_wallets w ON h.address = w.address
            WHERE w.user_id = ?
            ORDER BY h.timestamp DESC LIMIT 1
        '''
        cursor = await db.execute(query, (chat_id,))
        row = await cursor.fetchone()
        
        if not row:
            await message.answer("🔍 Henüz kayıtlı bir işlem bulunamadı. Botun yeni bir işlem yakalamasını beklemelisin veya veritabanı sıfırlanmış olabilir.")
            return
        
        dt = datetime.fromtimestamp(row['timestamp']).strftime('%H:%M:%S')
        
        name_display = f"👤 Cüzdan: <b>{row['nickname']}</b> (<code>{row['address']}</code>)" if row['nickname'] else f"👤 Cüzdan: <code>{row['address']}</code>"
        
        resp = "🕒 <b>Son Yakalanan İşlem:</b>\n\n"
        resp += f"{name_display}\n"
        resp += f"⏰ Zaman: {dt}\n"
        resp += f"🔗 Link: <a href='https://polygonscan.com/tx/{row['tx_hash']}'>PolygonScan Üzerinde Gör</a>"
        
        await message.answer(resp, parse_mode="HTML", disable_web_page_preview=True)
