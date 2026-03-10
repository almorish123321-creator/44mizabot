#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════╗
║     🤖 بوت النشر الخارق - الإصدار الأسطوري 💪                ║
║     مع 44 ميزة متطورة + تشفير + ردود تلقائية                 ║
╚═══════════════════════════════════════════════════════════════╝
"""

import asyncio
import re
import os
import random
import json
import sqlite3
import sys
import logging
import shutil
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from flask import Flask, jsonify
from threading import Thread

# ==================== الإعدادات الأساسية (تعديل للبيئة السحابية) ====================

API_ID = int(os.environ.get('API_ID', 33957094))
API_HASH = os.environ.get('API_HASH', "35e04f65846f09700aac0696a59f1a37")
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8568132127:AAG-4Mxkj7WxpQcVwUcX6GdGHRAfEMjQs_8")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 7853478744))

# ==================== إعدادات التشغيل ====================

SESSIONS_DIR = "sessions"
DATA_DIR = "data"
BACKUPS_DIR = "backups"
LOGS_DIR = "logs"
TEMP_DIR = "temp"
EXPORTS_DIR = "exports"
DB_PATH = f"{DATA_DIR}/bot_data.db"

for dir_path in [SESSIONS_DIR, DATA_DIR, BACKUPS_DIR, LOGS_DIR, TEMP_DIR, EXPORTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== خادم الويب المدمج (Keep-Alive) ====================
app = Flask(__name__)
@app.route('/')
def home(): return jsonify({'status': 'online', 'message': '🤖 البوت شغال بكافة الميزات!', 'time': str(datetime.now())})
@app.route('/ping')
def ping(): return 'pong', 200
def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ==================== نظام التسجيل ====================

class Logger:
    def __init__(self):
        log_file = f"{LOGS_DIR}/bot_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()]
        )
        self.logger = logging.getLogger('Bot')
    
    def info(self, msg): self.logger.info(msg); print(f"ℹ️ {msg}")
    def warning(self, msg): self.logger.warning(msg); print(f"⚠️ {msg}")
    def error(self, msg): self.logger.error(msg); print(f"❌ {msg}")
    def success(self, msg): self.logger.info(f"✅ {msg}"); print(f"✅ {msg}")

logger = Logger()

# ==================== قاعدة البيانات المتكاملة ====================

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, updated_at TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (msg_id TEXT PRIMARY KEY, content TEXT, created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, session_file TEXT, added_at TIMESTAMP, last_active TIMESTAMP, status TEXT, total_posts INTEGER DEFAULT 0, success_posts INTEGER DEFAULT 0, failed_posts INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS groups (group_id TEXT PRIMARY KEY, group_name TEXT, group_username TEXT, group_type TEXT, members_count INTEGER DEFAULT 0, added_by TEXT, added_at TIMESTAMP, last_post TIMESTAMP, post_count INTEGER DEFAULT 0, is_blacklisted INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS posting_history (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, group_id TEXT, group_name TEXT, sent_at TIMESTAMP, status TEXT, error TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT, group_id TEXT, message TEXT, attempts INTEGER DEFAULT 0, created_at TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS auto_replies (id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, response TEXT, match_type TEXT DEFAULT 'exact', is_active INTEGER DEFAULT 1, created_at TIMESTAMP, updated_at TIMESTAMP)''')
        conn.commit(); conn.close()
        logger.success("قاعدة البيانات جاهزة")
    
    def save_setting(self, key, value):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)', (key, json.dumps(value), datetime.now()))
        conn.commit(); conn.close()
    
    def get_setting(self, key, default=None):
        conn = sqlite3.connect(self.db_path)
        result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        conn.close(); return json.loads(result[0]) if result else default
    
    def get_all_settings(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        conn.close(); return {key: json.loads(value) for key, value in rows}
    
    def save_message(self, msg_id, content):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO messages (msg_id, content, created_at) VALUES (?, ?, ?)', (msg_id, content, datetime.now()))
        conn.commit(); conn.close()
    
    def get_all_messages(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT msg_id, content FROM messages').fetchall()
        conn.close(); return {msg_id: content for msg_id, content in rows}
    
    def add_account(self, phone, session_file):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR REPLACE INTO accounts (phone, session_file, added_at, last_active, status) VALUES (?, ?, ?, ?, ?)', (phone, session_file, datetime.now(), datetime.now(), 'active'))
        conn.commit(); conn.close()
    
    def remove_account(self, phone):
        conn = sqlite3.connect(self.db_path)
        conn.execute('DELETE FROM accounts WHERE phone = ?', (phone,))
        conn.commit(); conn.close()
    
    def get_accounts(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT phone, session_file, status, total_posts, success_posts, failed_posts FROM accounts ORDER BY added_at DESC').fetchall()
        conn.close(); return rows
    
    def update_account_status(self, phone, status):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE accounts SET status = ?, last_active = ? WHERE phone = ?', (status, datetime.now(), phone))
        conn.commit(); conn.close()
    
    def increment_account_posts(self, phone, success=True):
        conn = sqlite3.connect(self.db_path)
        if success: conn.execute('UPDATE accounts SET total_posts = total_posts + 1, success_posts = success_posts + 1 WHERE phone = ?', (phone,))
        else: conn.execute('UPDATE accounts SET total_posts = total_posts + 1, failed_posts = failed_posts + 1 WHERE phone = ?', (phone,))
        conn.commit(); conn.close()
    
    def add_group(self, group_id, group_name, group_username, group_type, members_count, added_by):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT OR IGNORE INTO groups (group_id, group_name, group_username, group_type, members_count, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?, ?)', (str(group_id), group_name or "بدون اسم", group_username, group_type, members_count or 0, added_by, datetime.now()))
        conn.commit(); conn.close()
    
    def update_group_post(self, group_id):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE groups SET post_count = post_count + 1, last_post = ? WHERE group_id = ?', (datetime.now(), str(group_id)))
        conn.commit(); conn.close()
    
    def blacklist_group(self, group_id):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE groups SET is_blacklisted = 1 WHERE group_id = ?', (str(group_id),))
        conn.commit(); conn.close()
    
    def whitelist_group(self, group_id):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE groups SET is_blacklisted = 0 WHERE group_id = ?', (str(group_id),))
        conn.commit(); conn.close()
    
    def get_all_groups(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT group_id, group_name, members_count, post_count, is_blacklisted, last_post FROM groups ORDER BY post_count DESC').fetchall()
        conn.close(); return rows
    
    def get_blacklisted_groups(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT group_id, group_name FROM groups WHERE is_blacklisted = 1').fetchall()
        conn.close(); return rows
    
    def search_groups(self, query):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT group_id, group_name, members_count FROM groups WHERE group_name LIKE ? LIMIT 20', (f'%{query}%',)).fetchall()
        conn.close(); return rows
    
    def log_post(self, phone, group_id, group_name, status='success', error=None):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO posting_history (phone, group_id, group_name, sent_at, status, error) VALUES (?, ?, ?, ?, ?, ?)', (phone, str(group_id), group_name, datetime.now(), status, error))
        if status == 'success':
            self.increment_account_posts(phone, success=True)
            self.update_group_post(group_id)
        else:
            self.increment_account_posts(phone, success=False)
        conn.commit(); conn.close()
    
    def get_posting_stats(self, hours=24):
        since = datetime.now() - timedelta(hours=hours)
        conn = sqlite3.connect(self.db_path)
        total = conn.execute('SELECT COUNT(*) FROM posting_history WHERE sent_at > ?', (since,)).fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM posting_history WHERE sent_at > ? AND status = 'success'", (since,)).fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM posting_history WHERE sent_at > ? AND status = 'failed'", (since,)).fetchone()[0]
        conn.close(); return {'total': total, 'success': success, 'failed': failed}
    
    def get_recent_posts(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT phone, group_name, status, sent_at FROM posting_history ORDER BY sent_at DESC LIMIT ?', (limit,)).fetchall()
        conn.close(); return rows
    
    def add_to_queue(self, phone, group_id, message):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO queue (phone, group_id, message, created_at) VALUES (?, ?, ?, ?)', (phone, str(group_id), message, datetime.now()))
        conn.commit(); conn.close()

    def get_queue(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT id, phone, group_id, message, attempts FROM queue ORDER BY created_at ASC').fetchall()
        conn.close(); return rows

    def add_auto_reply(self, keyword, response):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO auto_replies (keyword, response, created_at, updated_at) VALUES (?, ?, ?, ?)', (keyword, response, datetime.now(), datetime.now()))
        conn.commit(); conn.close()

    def get_auto_replies(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute('SELECT id, keyword, response, match_type, is_active FROM auto_replies').fetchall()
        conn.close(); return rows

    def delete_auto_reply(self, rid):
        conn = sqlite3.connect(self.db_path)
        conn.execute('DELETE FROM auto_replies WHERE id = ?', (rid,))
        conn.commit(); conn.close()

    def toggle_auto_reply(self, rid, status):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE auto_replies SET is_active = ? WHERE id = ?', (1 if status else 0, rid))
        conn.commit(); conn.close()

    def create_backup(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{BACKUPS_DIR}/backup_{timestamp}.db"
        shutil.copy2(self.db_path, backup_file)
        return backup_file

db = Database()

# ==================== المتغيرات العامة ====================

USER_CLIENTS = {}
MESSAGES = db.get_all_messages()
TEMP = {}
SETTINGS = {
    'interval': 3,
    'encryption': True,
    'auto_join_enabled': True,
    'max_groups_per_account': 50,
    'delay_between_accounts': 2,
    'auto_backup': True
}
SETTINGS.update(db.get_all_settings())
is_posting = False

# ==================== وظائف مساعدة ====================

def format_number(n):
    if n >= 1000000: return f"{n/1000000:.1f}M"
    if n >= 1000: return f"{n/1000:.1f}K"
    return str(n)

def encrypt_text(text):
    if not SETTINGS.get('encryption'): return text
    chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
    words = text.split()
    return " ".join([w + (random.choice(chars) if random.random() > 0.5 else "") for w in words])

# ==================== الأزرار ولوحات التحكم ====================

def main_buttons():
    enc_status = "✅ مفعل" if SETTINGS['encryption'] else "❌ معطل"
    post_icon = "🚀" if is_posting else "🛑"
    return [
        [Button.inline("➕ إضافة حساب", b"add"), Button.inline("🗑 حذف حساب", b"del_list")],
        [Button.inline("📝 ضبط الرسالة", b"msg"), Button.inline("⏱ ضبط الوقت", b"time")],
        [Button.inline(f"{post_icon} بدء النشر", b"start_p"), Button.inline("🛑 إيقاف النشر", b"stop_p")],
        [Button.inline(f"🛡 التشفير: {enc_status}", b"toggle_enc"), Button.inline("📊 الحالة", b"status")],
        [Button.inline("📢 المجموعات", b"view_chats"), Button.inline("⚙️ إعدادات متقدمة", b"advanced")],
        [Button.inline("📈 إحصائيات", b"stats"), Button.inline("🔄 إعادة تشغيل", b"restart")],
        [Button.inline("📋 سجل النشر", b"history"), Button.inline("💾 نسخ احتياطي", b"backup")],
        [Button.inline("🤖 ميزات خارقة", b"super_features"), Button.inline("📊 تقارير", b"reports")]
    ]

def advanced_buttons():
    return [
        [Button.inline("📥 استيراد مجموعات", b"import_groups"), Button.inline("🔍 بحث عن مجموعات", b"search_groups")],
        [Button.inline("🚫 قائمة المحظورات", b"blacklist_menu"), Button.inline("📊 إحصائيات تفصيلية", b"detailed_stats")],
        [Button.inline("💾 إعدادات النسخ", b"backup_settings"), Button.inline("📤 تصدير البيانات", b"export_data")],
        [Button.inline("⬅️ عودة", b"back")]
    ]

def groups_buttons():
    return [
        [Button.inline("🔄 تحديث القائمة", b"refresh_groups"), Button.inline("🚫 حظر مجموعة", b"add_blacklist")],
        [Button.inline("📊 إحصائيات المجموعات", b"group_stats"), Button.inline("📥 قائمة الانتظار", b"view_queue")],
        [Button.inline("⬅️ عودة", b"back")]
    ]

def blacklist_buttons():
    return [
        [Button.inline("➕ حظر مجموعة", b"add_blacklist"), Button.inline("✅ إزالة حظر", b"remove_blacklist")],
        [Button.inline("⬅️ عودة", b"advanced")]
    ]

def super_features_buttons():
    return [
        [Button.inline("🤖 الردود التلقائية", b"auto_reply_menu"), Button.inline("🔐 تجربة التشفير", b"test_encryption")],
        [Button.inline("📊 تحليل المجموعات", b"analyze_groups"), Button.inline("🎯 استهداف ذكي", b"smart_target")],
        [Button.inline("📅 جدولة النشر", b"schedule"), Button.inline("📊 توقع الأداء", b"prediction")],
        [Button.inline("⬅️ عودة", b"back")]
    ]

def auto_reply_buttons():
    return [
        [Button.inline("➕ إضافة رد", b"add_reply"), Button.inline("🗑 حذف رد", b"del_reply_menu")],
        [Button.inline("🔄 تفعيل/تعطيل", b"toggle_reply_menu"), Button.inline("📋 عرض الكل", b"list_replies")],
        [Button.inline("⬅️ عودة", b"super_features")]
    ]

# ==================== معالجات الأحداث ====================

async def start_handler(event):
    if event.sender_id != ADMIN_ID: return
    accounts = db.get_accounts()
    groups = db.get_all_groups()
    stats = db.get_posting_stats()
    text = (f"🤖 **مرحباً بك في بوت النشر الخارق!**\n\n"
            f"📊 **نظرة عامة:**\n"
            f"• الحسابات النشطة: `{len(USER_CLIENTS)}/{len(accounts)}`\n"
            f"• المجموعات المسجلة: `{len(groups)}`\n"
            f"• منشورات اليوم: `{stats['total']}` (✅ {stats['success']} | ❌ {stats['failed']})\n"
            f"• حالة النشر: `{'🚀 يعمل' if is_posting else '🛑 متوقف'}`\n\n"
            f"💡 استخدم الأزرار أدناه للتحكم:")
    await event.respond(text, buttons=main_buttons())

async def callback_handler(event):
    global is_posting
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode()
    
    if data == "back": await event.edit("👋 لوحة التحكم الرئيسية:", buttons=main_buttons())
    elif data == "advanced": await event.edit("⚙️ الإعدادات المتقدمة:", buttons=advanced_buttons())
    elif data == "view_chats": await show_groups(event)
    elif data == "blacklist_menu": await show_blacklist(event)
    elif data == "super_features": await event.edit("🤖 الميزات الخارقة:", buttons=super_features_buttons())
    elif data == "auto_reply_menu": await auto_reply_menu(event)
    elif data == "start_p":
        if not is_posting:
            is_posting = True; asyncio.create_task(poster())
            await event.answer("🚀 تم بدء النشر بنجاح!", alert=True)
            await event.edit(buttons=main_buttons())
        else: await event.answer("⚠️ النشر يعمل بالفعل!", alert=True)
    elif data == "stop_p":
        is_posting = False; await event.answer("🛑 تم إيقاف النشر", alert=True)
        await event.edit(buttons=main_buttons())
    elif data == "toggle_enc":
        SETTINGS['encryption'] = not SETTINGS['encryption']
        db.save_setting('encryption', SETTINGS['encryption'])
        await event.edit(buttons=main_buttons())
    elif data == "status":
        stats = db.get_posting_stats()
        await event.answer(f"📊 إحصائيات 24 ساعة:\n✅ نجاح: {stats['success']}\n❌ فشل: {stats['failed']}\n📦 الإجمالي: {stats['total']}", alert=True)
    elif data == "msg":
        TEMP[ADMIN_ID] = "msg"
        await event.respond("📝 أرسل نص الإعلان الجديد:")
    elif data == "time":
        TEMP[ADMIN_ID] = "time"
        await event.respond("⏱ أرسل الفاصل الزمني بالثواني (1-60):")
    elif data == "add":
        TEMP[ADMIN_ID] = "phone"
        await event.respond("📱 أرسل رقم الهاتف مع مفتاح الدولة (مثال: +9665xxxxxxx):")
    elif data == "del_list": await show_delete_list(event)
    elif data.startswith("rm_"): await delete_account(event, data[3:])
    elif data == "refresh_groups": await refresh_groups(event)
    elif data == "add_blacklist":
        TEMP[ADMIN_ID] = "add_blacklist"
        await event.respond("🚫 أرسل اسم المجموعة لحظرها:")
    elif data == "remove_blacklist": await show_remove_blacklist(event)
    elif data.startswith("unblack_"): await remove_from_blacklist(event, data[8:])
    elif data == "group_stats": await show_group_stats(event)
    elif data == "view_queue": await show_queue(event)
    elif data == "detailed_stats": await show_detailed_stats(event)
    elif data == "history": await show_posting_history(event)
    elif data == "backup": await create_backup(event)
    elif data == "backup_settings": await show_backup_settings(event)
    elif data == "export_data": await export_data(event)
    elif data == "search_groups":
        TEMP[ADMIN_ID] = "search_groups"
        await event.respond("🔍 أرسل كلمة للبحث في المجموعات:")
    elif data == "import_groups":
        TEMP[ADMIN_ID] = "import_groups"
        await event.respond("📥 أرسل روابط المجموعات (رابط في كل سطر):")
    elif data == "restart":
        await event.respond("🔄 جاري إعادة التشغيل...")
        os.execl(sys.executable, sys.executable, *sys.argv)
    elif data == "add_reply": await add_auto_reply_handler(event)
    elif data == "list_replies": await list_auto_replies(event)
    elif data == "del_reply_menu": await delete_auto_reply_menu(event)
    elif data.startswith("del_reply_"): await delete_auto_reply(event, data[10:])
    elif data == "toggle_reply_menu": await toggle_auto_reply_menu(event)
    elif data.startswith("toggle_reply_"): await toggle_auto_reply(event, data[13:])
    elif data == "test_encryption": await test_encryption(event)
    elif data == "analyze_groups": await analyze_groups(event)
    elif data == "smart_target": await show_smart_target(event)
    elif data == "schedule": await show_schedule(event)
    elif data == "prediction": await show_prediction(event)

# دمج كافة الدوال الفرعية (Stats, History, Groups, etc.)
async def show_detailed_stats(event):
    accounts = db.get_accounts()
    groups = db.get_all_groups()
    text = "📊 **إحصائيات تفصيلية**\n\n**أفضل الحسابات:**\n"
    for phone, _, status, posts, success, failed in sorted(accounts, key=lambda x: x[3], reverse=True)[:5]:
        rate = (success / posts * 100) if posts > 0 else 0
        text += f"• {phone[-8:]}: {posts} منشور ({rate:.1f}%)\n"
    text += "\n**أفضل المجموعات:**\n"
    for gid, name, members, posts, bl, last in sorted(groups, key=lambda x: x[3], reverse=True)[:5]:
        text += f"• {name[:20]}: {posts} منشور\n"
    await event.edit(text, buttons=advanced_buttons())

async def show_posting_history(event):
    recent = db.get_recent_posts(15)
    text = "📋 **آخر 15 عملية نشر**\n\n"
    for phone, group, status, sent_at in recent:
        time_str = datetime.fromisoformat(sent_at).strftime('%H:%M:%S')
        icon = "✅" if status == 'success' else "❌"
        text += f"{icon} {time_str} - {group[:20]}\n"
    await event.edit(text, buttons=advanced_buttons())

async def show_delete_list(event):
    accounts = db.get_accounts()
    if not accounts: return await event.answer("❌ لا توجد حسابات", alert=True)
    btns = []
    for phone, session, status, posts, success, failed in accounts[:10]:
        short = phone[-8:] if len(phone) > 8 else phone
        status_icon = "🟢" if status == 'active' else "🔴"
        btns.append([Button.inline(f"{status_icon} {short} ({posts})", f"rm_{phone}".encode())])
    btns.append([Button.inline("⬅️ عودة", b"back")])
    await event.edit("🗑 اختر حساباً للحذف", buttons=btns)

async def show_groups(event):
    groups = db.get_all_groups()
    blacklisted = db.get_blacklisted_groups()
    text = f"📢 **المجموعات**\nالإجمالي: {len(groups)}\nالمحظور: {len(blacklisted)}\n\n"
    for gid, name, members, posts, bl, last in groups[:15]:
        name_short = name[:25] if name else "بدون اسم"
        status = "🚫" if bl else "✅"
        members_fmt = format_number(members) if members else "?"
        text += f"{status} {name_short}\n   👥 {members_fmt} | 📨 {posts}\n"
    if len(groups) > 15: text += f"\n... و {len(groups) - 15} مجموعة أخرى"
    await event.edit(text, buttons=main_buttons())

async def show_blacklist(event):
    blacklisted = db.get_blacklisted_groups()
    if not blacklisted: await event.edit("📭 لا توجد مجموعات محظورة", buttons=blacklist_buttons()); return
    text = "🚫 **المجموعات المحظورة**\n\n"
    for gid, name in blacklisted[:20]: text += f"• {name[:40]}\n"
    if len(blacklisted) > 20: text += f"\n... و {len(blacklisted) - 20} مجموعة أخرى"
    await event.edit(text, buttons=blacklist_buttons())

async def show_remove_blacklist(event):
    blacklisted = db.get_blacklisted_groups()
    if not blacklisted: return await event.answer("❌ لا توجد محظورات", alert=True)
    btns = []
    for gid, name in blacklisted[:10]: btns.append([Button.inline(f"✅ {name[:20]}", f"unblack_{gid}".encode())])
    btns.append([Button.inline("⬅️ عودة", b"blacklist_menu")])
    await event.edit("✅ اختر مجموعة لإزالتها من المحظورات", buttons=btns)

async def show_group_stats(event):
    groups = db.get_all_groups()
    if not groups: return await event.answer("❌ لا توجد مجموعات", alert=True)
    most_active = sorted(groups, key=lambda x: x[3], reverse=True)[:5]
    largest = sorted(groups, key=lambda x: x[2] or 0, reverse=True)[:5]
    text = "📊 **إحصائيات المجموعات**\n\n**الأكثر نشاطاً:**\n"
    for gid, name, members, posts, bl, last in most_active: text += f"• {name[:25]}: {posts} منشور\n"
    text += "\n**الأكبر عدداً:**\n"
    for gid, name, members, posts, bl, last in largest:
        members_fmt = format_number(members) if members else "?"
        text += f"• {name[:25]}: {members_fmt} عضو\n"
    await event.edit(text, buttons=groups_buttons())

async def show_queue(event):
    queue = db.get_queue()
    if not queue: await event.edit("📭 قائمة الانتظار فارغة", buttons=groups_buttons()); return
    text = f"📥 **قائمة الانتظار** ({len(queue)} رسالة)\n\n"
    for qid, phone, gid, msg, attempts in queue[:10]: text += f"• {msg[:30]}...\n  📱 {phone[-8:]} | 🔄 {attempts}\n"
    await event.edit(text, buttons=groups_buttons())

async def show_backup_settings(event):
    backups = sorted(Path(BACKUPS_DIR).glob('backup_*.db'))
    total_size = sum(f.stat().st_size for f in backups) / 1024 / 1024
    text = f"💾 **إعدادات النسخ الاحتياطي**\n\n📊 عدد النسخ: {len(backups)}\n💾 الحجم: {total_size:.1f} MB\n⚙️ النسخ التلقائي: {'✅' if SETTINGS.get('auto_backup') else '❌'}"
    await event.edit(text, buttons=advanced_buttons())

async def auto_reply_menu(event):
    replies = db.get_auto_replies()
    text = f"🤖 **الردود التلقائية**\n\n📊 عدد الردود: {len(replies)}\n\n"
    if replies:
        for i, (rid, keyword, response, match_type, active) in enumerate(replies[:10], 1):
            status = "🟢 مفعل" if active else "🔴 معطل"
            text += f"{i}. `{keyword}` → {response[:30]}...\n   {status}\n\n"
    else: text += "لا توجد ردود تلقائية حالياً.\n"
    text += "\n🔽 **اختر إجراء:**"
    await event.edit(text, buttons=auto_reply_buttons())

async def add_auto_reply_handler(event):
    await event.edit("🔑 **أرسل الكلمة المفتاحية للرد:**\nمثال: `مرحبا`")
    TEMP[ADMIN_ID] = {"s": "auto_keyword"}

async def auto_reply_keyword_handler(event, state):
    TEMP[ADMIN_ID] = {"s": "auto_response", "keyword": event.text.strip()}
    await event.respond("💬 **أرسل نص الرد:**")

async def auto_reply_response_handler(event, state):
    keyword = state['keyword']; response = event.text.strip()
    db.add_auto_reply(keyword, response)
    await event.respond(f"✅ **تم إضافة الرد بنجاح!**\n🔑 `{keyword}` → 💬 {response[:50]}...", buttons=super_features_buttons())
    TEMP.pop(ADMIN_ID)

async def list_auto_replies(event):
    replies = db.get_auto_replies()
    if not replies: return await event.answer("❌ لا توجد ردود!", alert=True)
    text = "📋 **جميع الردود التلقائية**\n\n"
    for rid, keyword, response, match_type, active in replies:
        status = "🟢" if active else "🔴"
        text += f"{status} `{keyword}` → {response[:50]}\n"
    await event.edit(text, buttons=auto_reply_buttons())

async def delete_auto_reply_menu(event):
    replies = db.get_auto_replies()
    if not replies: return await event.answer("❌ لا توجد ردود!", alert=True)
    btns = []
    for rid, keyword, response, match_type, active in replies[:10]:
        btns.append([Button.inline(f"🗑 {keyword}", f"del_reply_{rid}".encode())])
    btns.append([Button.inline("⬅️ عودة", b"auto_reply_menu")])
    await event.edit("🗑 **اختر رداً للحذف:**", buttons=btns)

async def delete_auto_reply(event, reply_id):
    db.delete_auto_reply(int(reply_id))
    await event.answer("✅ تم الحذف", alert=True)
    await delete_auto_reply_menu(event)

async def toggle_auto_reply_menu(event):
    replies = db.get_auto_replies()
    if not replies: return await event.answer("❌ لا توجد ردود!", alert=True)
    btns = []
    for rid, keyword, response, match_type, active in replies[:10]:
        status = "🟢" if active else "🔴"
        btns.append([Button.inline(f"{status} {keyword}", f"toggle_reply_{rid}".encode())])
    btns.append([Button.inline("⬅️ عودة", b"auto_reply_menu")])
    await event.edit("🔄 **اختر رداً للتفعيل/التعطيل:**", buttons=btns)

async def toggle_auto_reply(event, reply_id):
    replies = db.get_auto_replies()
    for rid, keyword, response, match_type, active in replies:
        if rid == int(reply_id):
            db.toggle_auto_reply(rid, not active)
            await event.answer(f"✅ تم {'تفعيل' if not active else 'تعطيل'} {keyword}", alert=True)
            break
    await toggle_auto_reply_menu(event)

async def test_encryption(event):
    original = "رسالة تجريبية لاختبار التشفير"
    encrypted = encrypt_text(original)
    text = f"🔐 **اختبار التشفير**\n\n📝 الأصلي: {original}\n🔒 المشفر: {encrypted}\n📊 الطول: {len(original)} → {len(encrypted)} حرف"
    await event.edit(text, buttons=super_features_buttons())

async def analyze_groups(event):
    groups = db.get_all_groups()
    if not groups: return await event.answer("❌ لا توجد مجموعات", alert=True)
    total_members = sum(g[2] or 0 for g in groups)
    active = [g for g in groups if g[3] > 0]
    text = f"📊 **تحليل المجموعات**\n\n📈 الإجمالي: {len(groups)}\n👥 الأعضاء: {format_number(total_members)}\n📊 متوسط: {format_number(total_members/len(groups))}\n✅ نشطة: {len(active)}\n❌ خاملة: {len(groups)-len(active)}\n📊 نسبة النشاط: {len(active)/len(groups)*100:.1f}%"
    await event.edit(text, buttons=super_features_buttons())

async def show_smart_target(event):
    groups = db.get_all_groups()
    small = len([g for g in groups if (g[2] or 0) < 1000])
    medium = len([g for g in groups if 1000 <= (g[2] or 0) < 10000])
    large = len([g for g in groups if (g[2] or 0) >= 10000])
    text = f"🎯 **الاستهداف الذكي**\n\n📊 صغيرة (<1K): {small}\n📊 متوسطة (1K-10K): {medium}\n📊 كبيرة (>10K): {large}\n\n💡 استهدف المتوسطة والنشطة أولاً"
    await event.edit(text, buttons=super_features_buttons())

async def show_schedule(event):
    text = "📅 **جدولة النشر**\n\n⏰ الجدول المقترح:\n• 08:00-12:00: نشاط متوسط\n• 12:00-18:00: نشاط عالي\n• 18:00-00:00: نشاط متوسط\n• 00:00-08:00: منخفض\n\n⚙️ قيد التطوير 🚧"
    await event.edit(text, buttons=super_features_buttons())

async def show_prediction(event):
    stats = db.get_posting_stats()
    text = f"📊 **توقع الأداء**\n\n📈 اليوم: {stats['total']} رسالة\n📊 غداً (متوقع): {stats['total'] * 1.1:.0f}\n✅ نسبة النجاح: {stats['success']/(stats['total'] or 1)*100:.1f}%\n\n💡 توصيات: استمر على نفس الوتيرة"
    await event.edit(text, buttons=super_features_buttons())

async def export_data(event):
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = f"{EXPORTS_DIR}/export_{timestamp}.json"
        data = {'settings': SETTINGS, 'messages': MESSAGES, 'accounts': db.get_accounts(), 'groups': db.get_all_groups()}
        with open(export_file, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        await event.answer(f"✅ تم التصدير إلى {export_file}", alert=True)
    except Exception as e: await event.answer(f"❌ فشل التصدير: {e}", alert=True)

async def delete_account(event, phone):
    if phone in USER_CLIENTS:
        await USER_CLIENTS[phone].disconnect(); del USER_CLIENTS[phone]
    db.remove_account(phone)
    session_file = f"{SESSIONS_DIR}/{phone}.session"
    if os.path.exists(session_file): os.remove(session_file)
    await event.answer(f"✅ تم حذف {phone}", alert=True)
    await show_delete_list(event)

async def remove_from_blacklist(event, group_id):
    db.whitelist_group(group_id); await event.answer("✅ تمت الإزالة", alert=True); await show_blacklist(event)

async def refresh_groups(event):
    await event.answer("🔄 جاري تحديث المجموعات..."); count = 0
    for phone, client in USER_CLIENTS.items():
        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    members = getattr(dialog.entity, 'participants_count', 0)
                    db.add_group(dialog.id, dialog.name, getattr(dialog.entity, 'username', None), 'group' if dialog.is_group else 'channel', members, phone)
                    count += 1
        except: pass
    await event.answer(f"✅ تم تحديث {count} مجموعة"); await event.edit("🗂 إدارة المجموعات:", buttons=groups_buttons())

async def create_backup(event):
    try:
        backup_file = db.create_backup()
        await event.answer(f"✅ تم إنشاء النسخة: {os.path.basename(backup_file)}", alert=True)
    except Exception as e: await event.answer(f"❌ فشل النسخ: {e}", alert=True)

async def refresh_groups_async():
    count = 0
    for phone, client in USER_CLIENTS.items():
        try:
            async for dialog in client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    members = getattr(dialog.entity, 'participants_count', 0)
                    db.add_group(dialog.id, dialog.name, getattr(dialog.entity, 'username', None), 'group' if dialog.is_group else 'channel', members, phone)
                    count += 1
        except: pass
    logger.info(f"✅ تم تحديث {count} مجموعة")

async def text_handler(event):
    state = TEMP.get(ADMIN_ID); text = event.message.text.strip()
    if event.is_group and event.message.text and not event.out:
        replies = db.get_auto_replies()
        msg_text = event.message.text.lower()
        for rid, keyword, response, match_type, active in replies:
            if not active: continue
            if (match_type == 'exact' and msg_text == keyword.lower()) or \
               (match_type == 'contains' and keyword.lower() in msg_text) or \
               (match_type == 'startswith' and msg_text.startswith(keyword.lower())):
                await event.reply(response); break
    links = re.findall(r"(https?://t\.me/(?:joinchat/|\+)[a-zA-Z0-9_-]+|https?://t\.me/[a-zA-Z0-9_]+)", text)
    if links and SETTINGS.get('auto_join_enabled', True) and USER_CLIENTS:
        await handle_auto_join(event, links); return
    if isinstance(state, dict) and state.get("s") == "auto_keyword": await auto_reply_keyword_handler(event, state)
    elif isinstance(state, dict) and state.get("s") == "auto_response": await auto_reply_response_handler(event, state)
    elif state == "msg":
        MESSAGES["1"] = text; db.save_message("1", text); TEMP.pop(ADMIN_ID)
        await event.respond("✅ تم حفظ الإعلان!", buttons=main_buttons())
    elif state == "time":
        try:
            interval = int(text)
            if 1 <= interval <= 60:
                SETTINGS['interval'] = interval; db.save_setting('interval', interval); TEMP.pop(ADMIN_ID)
                await event.respond(f"✅ تم ضبط الوقت على {text} ثانية", buttons=main_buttons())
            else: await event.respond("❌ الرجاء إدخال قيمة بين 1 و 60")
        except: await event.respond("❌ أرسل رقماً فقط")
    elif state == "add_blacklist":
        groups = db.search_groups(text)
        if groups:
            for gid, name, members in groups[:5]: db.blacklist_group(gid)
            await event.respond(f"✅ تم حظر {len(groups[:5])} مجموعة")
        else: await event.respond("❌ لم يتم العثور على مجموعات")
        TEMP.pop(ADMIN_ID); await event.respond("⚙️ الإعدادات المتقدمة:", buttons=advanced_buttons())
    elif state == "search_groups":
        groups = db.search_groups(text)
        if groups:
            msg = f"🔍 **نتائج البحث عن '{text}':**\n\n"
            for gid, name, members in groups:
                members_fmt = format_number(members) if members else "?"
                msg += f"• {name[:40]}\n  👥 {members_fmt}\n"
            await event.respond(msg)
        else: await event.respond("❌ لا توجد نتائج")
        TEMP.pop(ADMIN_ID)
    elif state == "import_groups":
        lines = text.split('\n'); count = 0
        for line in lines[:5]:
            link = line.strip()
            if link and ('t.me' in link or 'telegram' in link): await handle_auto_join(event, [link]); count += 1
        await event.respond(f"✅ تمت معالجة {count} رابط"); TEMP.pop(ADMIN_ID)
    elif state == "phone": await handle_phone_login(event, text)

async def handle_auto_join(event, links):
    await event.respond(f"⏳ جاري الانضمام لـ {len(links)} مجموعة..."); success = 0; failed = 0
    for link in links[:3]:
        for phone, client in USER_CLIENTS.items():
            try:
                if "joinchat" in link or "+" in link:
                    hash_part = link.split('/')[-1].replace('+', '')
                    await client(ImportChatInviteRequest(hash_part))
                else: await client(JoinChannelRequest(link))
                success += 1; await event.respond(f"✅ {phone} انضم إلى {link[:30]}..."); await asyncio.sleep(2)
            except Exception as e: failed += 1; await event.respond(f"❌ {phone}: {str(e)[:50]}")
    await event.respond(f"📊 **النتيجة:**\n✅ نجاح: {success}\n❌ فشل: {failed}")

async def handle_phone_login(event, phone):
    client = TelegramClient(f"{SESSIONS_DIR}/{phone}", API_ID, API_HASH)
    await client.connect()
    try:
        await client.send_code_request(phone)
        TEMP[ADMIN_ID] = {"s": "code", "p": phone, "c": client}
        await event.respond(f"📩 تم إرسال الكود لـ {phone}\nأرسل الكود الآن:")
    except Exception as e: await event.respond(f"❌ خطأ: {str(e)[:100]}")

async def handle_code_verification(event, state, code):
    try:
        client = state["c"]; phone = state["p"]; await client.sign_in(phone, code)
        USER_CLIENTS[phone] = client; db.add_account(phone, f"{SESSIONS_DIR}/{phone}.session")
        await event.respond(f"✅ تم تفعيل الحساب {phone} بنجاح!"); TEMP.pop(ADMIN_ID)
        asyncio.create_task(refresh_groups_async())
    except SessionPasswordNeededError:
        TEMP[ADMIN_ID]["s"] = "pass"; await event.respond("🔐 هذا الحساب محمي بكلمة سر\nأرسل كلمة المرور:")
    except Exception as e: await event.respond(f"❌ فشل: {str(e)[:100]}")

async def handle_password(event, state, password):
    try:
        await state["c"].sign_in(password=password); USER_CLIENTS[state["p"]] = state["c"]
        db.add_account(state["p"], f"{SESSIONS_DIR}/{state['p']}.session")
        await event.respond(f"✅ تم التفعيل بنجاح!"); TEMP.pop(ADMIN_ID)
        asyncio.create_task(refresh_groups_async())
    except Exception as e: await event.respond(f"❌ خطأ في كلمة المرور: {str(e)[:100]}")

async def poster():
    global is_posting
    logger.info("🚀 بدء النشر...")
    while is_posting:
        try:
            if not USER_CLIENTS or "1" not in MESSAGES: await asyncio.sleep(5); continue
            txt = MESSAGES["1"]
            for phone, client in list(USER_CLIENTS.items()):
                if not is_posting: break
                try:
                    groups_sent = 0
                    async for dialog in client.iter_dialogs():
                        if not is_posting: break
                        if dialog.is_group or dialog.is_channel:
                            blacklisted = [g[0] for g in db.get_blacklisted_groups()]
                            if str(dialog.id) in blacklisted: continue
                            if groups_sent >= SETTINGS.get('max_groups_per_account', 50): break
                            try:
                                members = getattr(dialog.entity, 'participants_count', 0)
                                db.add_group(dialog.id, dialog.name, getattr(dialog.entity, 'username', None), 'group' if dialog.is_group else 'channel', members, phone)
                                msg = encrypt_text(txt); await client.send_message(dialog.id, msg)
                                db.log_post(phone, dialog.id, dialog.name, 'success')
                                groups_sent += 1; logger.info(f"✅ {dialog.name[:30]}")
                                await asyncio.sleep(SETTINGS['interval'])
                            except FloodWaitError as e: logger.warning(f"⚠️ Flood wait {e.seconds}s"); await asyncio.sleep(e.seconds)
                            except Exception as e: logger.error(f"❌ خطأ: {e}"); db.log_post(phone, dialog.id, dialog.name, 'failed', str(e)[:100])
                    await asyncio.sleep(SETTINGS.get('delay_between_accounts', 2))
                except Exception as e: logger.error(f"❌ خطأ في حساب {phone}: {e}")
            await asyncio.sleep(5)
        except Exception as e: logger.error(f"❌ خطأ في النشر: {e}"); await asyncio.sleep(10)
    logger.info("🛑 توقف النشر")

async def restore_sessions():
    restored = 0
    for phone, session_file, status, posts, success, failed in db.get_accounts():
        try:
            if os.path.exists(session_file):
                client = TelegramClient(session_file, API_ID, API_HASH)
                await client.connect()
                if await client.is_user_authorized():
                    USER_CLIENTS[phone] = client; db.update_account_status(phone, 'active'); restored += 1; logger.info(f"✅ استعادة {phone}")
                else: db.update_account_status(phone, 'unauthorized')
            else: logger.warning(f"⚠️ ملف الجلسة مفقود: {session_file}")
        except Exception as e: logger.error(f"❌ فشل استعادة {phone}: {e}"); db.update_account_status(phone, 'error')
    logger.info(f"✅ تم استعادة {restored} حساب")

async def main():
    print("="*60); print("🚀 بوت النشر الخارق - الإصدار الكامل مع الردود التلقائية"); print("="*60)
    Thread(target=run_web, daemon=True).start()
    await restore_sessions()
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(e): await start_handler(e)
    @bot.on(events.CallbackQuery())
    async def callback(e): await callback_handler(e)
    @bot.on(events.NewMessage)
    async def text(e):
        if e.message.text and e.sender_id == ADMIN_ID:
            state = TEMP.get(ADMIN_ID)
            if isinstance(state, dict) and state.get("s") == "code": await handle_code_verification(e, state, e.message.text.strip())
            elif isinstance(state, dict) and state.get("s") == "pass": await handle_password(e, state, e.message.text.strip())
            else: await text_handler(e)
        elif e.is_group and e.message.text: await text_handler(e)
    logger.success("✅ البوت جاهز! أرسل /start"); await bot.run_until_disconnected()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: logger.info("👋 تم إيقاف البوت")
    except Exception as e: logger.critical(f"💥 خطأ: {e}"); time.sleep(5); os.execl(sys.executable, sys.executable, *sys.argv)

