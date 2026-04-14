import aiosqlite
import os
import atexit
from config import DB_PATH

DB_DIR = os.path.dirname(DB_PATH)

async def init_db():
    if not os.path.exists(DB_DIR) and DB_DIR != "":
        os.makedirs(DB_DIR)
        
    async with aiosqlite.connect(DB_PATH) as db:
        # Create users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        # Create tracked_wallets table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tracked_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                address TEXT COLLATE NOCASE,
                last_seen_trade_id TEXT,
                last_seen_timestamp INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, address)
            )
        ''')

        # Create activity_history table for global deduplication
        await db.execute('''
            CREATE TABLE IF NOT EXISTS activity_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT,
                tx_hash TEXT,
                timestamp INTEGER,
                UNIQUE(address, tx_hash)
            )
        ''')
        await db.commit()

async def is_activity_seen(address: str, tx_hash: str) -> bool:
    """Checks if a specific transaction has already been processed for an address."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT 1 FROM activity_history WHERE address = ? AND tx_hash = ?',
            (address.lower(), tx_hash)
        )
        return await cursor.fetchone() is not None

async def record_activity(address: str, tx_hash: str, timestamp: int):
    """Records a transaction hash to prevent duplicate alerts."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO activity_history (address, tx_hash, timestamp) VALUES (?, ?, ?)',
            (address.lower(), tx_hash, timestamp)
        )
        # Keep only last 500 items per address to keep DB small but safe
        await db.execute('''
            DELETE FROM activity_history 
            WHERE address = ? AND id NOT IN (
                SELECT id FROM activity_history 
                WHERE address = ? 
                ORDER BY timestamp DESC LIMIT 500
            )
        ''', (address.lower(), address.lower()))
        await db.commit()

async def get_tracked_wallets():
    """Returns a list of dictionaries with all tracked wallets."""
    result = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM tracked_wallets') as cursor:
            async for row in cursor:
                result.append(dict(row))
    return result

async def get_user_tracked_wallets(user_id: int):
    result = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT address FROM tracked_wallets WHERE user_id = ?', (user_id,)) as cursor:
            async for row in cursor:
                result.append(row['address'])
    return result

async def add_tracked_wallet(user_id: int, address: str):
    address = address.lower()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        try:
            await db.execute(
                'INSERT INTO tracked_wallets (user_id, address) VALUES (?, ?)',
                (user_id, address)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False # Already tracking

async def remove_tracked_wallet(user_id: int, address: str):
    address = address.lower()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'DELETE FROM tracked_wallets WHERE user_id = ? AND address = ?',
            (user_id, address)
        )
        await db.commit()
        return cursor.rowcount > 0

async def update_last_seen(user_id: int, address: str, trade_id: str, timestamp: int):
    address = address.lower()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''UPDATE tracked_wallets 
               SET last_seen_trade_id = ?, last_seen_timestamp = ? 
               WHERE user_id = ? AND address = ?''',
            (trade_id, timestamp, user_id, address)
        )
        await db.commit()

async def ensure_default_track():
    """Seeds the DB with default tracking targets from env variables if provided."""
    from config import DEFAULT_CHAT_ID, DEFAULT_WALLET
    if not DEFAULT_CHAT_ID or not DEFAULT_WALLET:
        logging.info("No default track settings found in environment variables.")
        return
    
    try:
        # Robust parsing: strip quotes or spaces if user added them in Railway UI
        chat_id_str = DEFAULT_CHAT_ID.strip().replace('"', '').replace("'", "")
        chat_id = int(chat_id_str)
        address = DEFAULT_WALLET.strip().replace('"', '').replace("'", "").lower()
        
        async with aiosqlite.connect(DB_PATH) as db:
            db_dir = os.path.dirname(DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                
            await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (chat_id,))
            await db.execute(
                'INSERT OR IGNORE INTO tracked_wallets (user_id, address) VALUES (?, ?)',
                (chat_id, address)
            )
            await db.commit()
            logging.info(f"✅ SUCCESS: Default track initialized for {address} in chat {chat_id}")
    except Exception as e:
        logging.error(f"❌ ERROR seeding default track: {e}")
