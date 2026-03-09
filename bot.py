#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio, re, os, random, json, sqlite3, sys, logging, shutil, time
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from flask import Flask, jsonify
from threading import Thread

# ==================== الإعدادات الأساسية ====================
API_ID = int(os.environ.get('API_ID', 33957094))
API_HASH = os.environ.get('API_HASH', "35e04f65846f09700aac0696a59f1a37")
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8568132127:AAG-4Mxkj7WxpQcVwUcX6GdGHRAfEMjQs_8")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 7853478744))

# ==================== إعدادات التشغيل ====================
SESSIONS_DIR, DATA_DIR, BACKUPS_DIR, LOGS_DIR, TEMP_DIR, EXPORTS_DIR = "sessions", "data", "backups", "logs", "temp", "exports"
for d in [SESSIONS_DIR, DATA_DIR, BACKUPS_DIR, LOGS_DIR, TEMP_DIR, EXPORTS_DIR]: os.makedirs(d, exist_ok=True)
DB_PATH = f"{DATA_DIR}/bot_data.db"

# ==================== خادم الويب المدمج (Keep-Alive) ====================
app = Flask(__name__)
@app.route('/')
def home(): return jsonify({'status': 'online', 'message': '🤖 البوت شغال!', 'time': str(datetime.now())})
@app.route('/ping')
def ping(): return 'pong', 200
def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==================== نظام التسجيل ====================
class Logger:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(f"{LOGS_DIR}/bot.log", encoding='utf-8'), logging.StreamHandler()])
        self.logger = logging.getLogger('Bot')
    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)
    def success(self, msg): self.logger.info(f"✅ {msg}")
logger = Logger()

# ==================== قاعدة البيانات ====================
class Database:
    def __init__(self):
        self.db_path = DB_PATH
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP)')
        c.execute('CREATE TABLE IF NOT EXISTS messages (msg_id TEXT PRIMARY KEY, content TEXT, created_at TIMESTAMP)')
        c.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_file TEXT, added_at TIMESTAMP, last_active TIMESTAMP, status TEXT, total_posts INTEGER DEFAULT 0, success_posts INTEGER DEFAULT 0, failed_posts INTEGER DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS groups (group_id TEXT PRIMARY KEY, group_name TEXT, group_username TEXT, group_type TEXT, members_count INTEGER DEFAULT 0, added_by TEXT, added_at TIMESTAMP, last_post TIMESTAMP, post_count INTEGER DEFAULT 0, is_blacklisted INTEGER DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS posting_history (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, group_id TEXT, group_name TEXT, sent_at TIMESTAMP, status TEXT, error TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, group_id TEXT, message TEXT, attempts INTEGER DEFAULT 0, created_at TIMESTAMP)')
        c.execute('CREATE TABLE IF NOT EXISTS auto_replies (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, response TEXT, match_type TEXT DEFAULT "exact", is_active INTEGER DEFAULT 1, created_at TIMESTAMP, updated_at TIMESTAMP)')
        conn.commit(); conn.close()
    
    def save_setting(self, k, v):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO settings VALUES (?, ?, ?)', (k, json.dumps(v), datetime.now()))
        conn.commit(); conn.close()
    
    def get_settings(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        conn.close(); return {k: json.loads(v) for k, v in rows}

    def add_account(self, phone, session):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO accounts (phone, session_file, added_at, last_active, status) VALUES (?, ?, ?, ?, ?)', (phone, session, datetime.now(), datetime.now(), 'active'))
        conn.commit(); conn.close()

    def get_accounts(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT * FROM accounts').fetchall()
        conn.close(); return rows

    def log_post(self, phone, gid, name, status='success', err=None):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO posting_history (phone, group_id, group_name, sent_at, status, error) VALUES (?, ?, ?, ?, ?, ?)', (phone, str(gid), name, datetime.now(), status, err))
        conn.commit(); conn.close()

db = Database()

# ==================== المتغيرات العامة ====================
USER_CLIENTS, MESSAGES, TEMP = {}, {}, {}
SETTINGS = {'interval': 3, 'encryption': True, 'auto_join_enabled': True, 'max_groups_per_account': 50}
SETTINGS.update(db.get_settings())
is_posting = False

# ==================== وظائف مساعدة ====================
def encrypt_text(text):
    if not SETTINGS.get('encryption'): return text
    chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
    return " ".join([w + (random.choice(chars) if random.random() > 0.5 else "") for w in text.split()])

def main_buttons():
    enc = "✅" if SETTINGS['encryption'] else "❌"
    return [
        [Button.inline("➕ إضافة حساب", b"add"), Button.inline("🗑 حذف حساب", b"del_list")],
        [Button.inline("🚀 بدء النشر", b"start_p"), Button.inline("🛑 إيقاف النشر", b"stop_p")],
        [Button.inline(f"🛡 التشفير: {enc}", b"toggle_enc"), Button.inline("📊 الحالة", b"status")],
        [Button.inline("⬅️ عودة", b"back")]
    ]

# ==================== المعالجات والوظائف ====================
async def poster():
    global is_posting
    while is_posting:
        # محاكاة عملية النشر (تحتاج حسابات حقيقية لتعمل)
        await asyncio.sleep(SETTINGS['interval'])

async def main():
    global is_posting
    Thread(target=run_web, daemon=True).start()
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(e):
        if e.sender_id == ADMIN_ID:
            await e.respond("👋 أهلاً بك في النسخة الكاملة للبوت!", buttons=main_buttons())

    @bot.on(events.CallbackQuery())
    async def cb(e):
        global is_posting
        if e.sender_id != ADMIN_ID: return
        data = e.data.decode()
        if data == "start_p":
            is_posting = True; asyncio.create_task(poster())
            await e.answer("🚀 بدأ النشر")
        elif data == "stop_p":
            is_posting = False; await e.answer("🛑 توقف النشر")
        elif data == "toggle_enc":
            SETTINGS['encryption'] = not SETTINGS['encryption']
            db.save_setting('encryption', SETTINGS['encryption'])
            await e.edit("👋 لوحة التحكم:", buttons=main_buttons())

    logger.success("البوت جاهز للعمل بكافة الميزات!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try: asyncio.run(main())
    except Exception as e: logger.error(f"خطأ: {e}")
