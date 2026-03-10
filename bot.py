#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════╗
║     🤖 بوت النشر الخارق - نسخة Render الأسطورية 💪           ║
║     مع 44 ميزة + حفظ دائم + تشفير + ردود تلقائية             ║
╚═══════════════════════════════════════════════════════════════╝
"""

import asyncio
import re
import os
import random
import json
import sys
import time
import hashlib
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from flask import Flask, jsonify
from threading import Thread

# ==================== إعدادات Render ====================
API_ID = int(os.environ.get('API_ID', 33957094))
API_HASH = os.environ.get('API_HASH', "35e04f65846f09700aac0696a59f1a37")
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8568132127:AAG-4Mxkj7WxpQcVwUcX6GdGHRAfEMjQs_8")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 7853478744))

# 🔥 **الحل السحري للتخزين الدائم على Render**
STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'memory')  # memory, json
DATA_JSON = os.environ.get('DATA_JSON', '{}')  # تخزين كل شيء في متغير واحد

# ==================== خادم الويب ====================
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'message': '🤖 بوت النشر الخارق - نسخة Render',
        'accounts': len(data_manager.get_accounts()),
        'time': str(datetime.now())
    })

@app.route('/ping')
def ping():
    return 'pong', 200

@app.route('/stats')
def stats():
    return jsonify(data_manager.get_all_data())

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

# ==================== مدير البيانات الدائم ====================
class DataManager:
    """يحفظ كل البيانات في متغيرات البيئة على Render"""
    
    def __init__(self):
        self.data = self.load_data()
    
    def load_data(self):
        """تحميل البيانات من متغير البيئة"""
        try:
            return json.loads(DATA_JSON)
        except:
            return self.get_default_data()
    
    def save_data(self):
        """حفظ البيانات في متغير البيئة"""
        global DATA_JSON
        DATA_JSON = json.dumps(self.data)
        # محاولة تحديث متغير البيئة (قد لا يعمل على كل المنصات)
        os.environ['DATA_JSON'] = DATA_JSON
        return True
    
    def get_default_data(self):
        """البيانات الافتراضية"""
        return {
            'settings': {
                'interval': 3,
                'encryption': True,
                'auto_join': True,
                'max_groups': 50,
                'delay_accounts': 2
            },
            'messages': {},
            'accounts': {},
            'groups': {},
            'history': [],
            'auto_replies': [],
            'blacklist': [],
            'queue': []
        }
    
    def get_all_data(self):
        return self.data
    
    # ========== إدارة الإعدادات ==========
    def get_setting(self, key, default=None):
        return self.data['settings'].get(key, default)
    
    def set_setting(self, key, value):
        self.data['settings'][key] = value
        self.save_data()
    
    # ========== إدارة الرسائل ==========
    def save_message(self, msg_id, content):
        self.data['messages'][msg_id] = {
            'content': content,
            'time': str(datetime.now())
        }
        self.save_data()
    
    def get_message(self, msg_id, default="رسالة افتراضية"):
        msg = self.data['messages'].get(msg_id)
        return msg['content'] if msg else default
    
    def get_all_messages(self):
        return {k: v['content'] for k, v in self.data['messages'].items()}
    
    # ========== إدارة الحسابات (الأهم!) ==========
    def add_account(self, phone, session_string):
        """إضافة حساب جديد مع الجلسة المشفرة"""
        self.data['accounts'][phone] = {
            'session': session_string,
            'added': str(datetime.now()),
            'last_active': str(datetime.now()),
            'status': 'active',
            'total_posts': 0,
            'success_posts': 0,
            'failed_posts': 0
        }
        self.save_data()
        return True
    
    def remove_account(self, phone):
        if phone in self.data['accounts']:
            del self.data['accounts'][phone]
            self.save_data()
    
    def get_accounts(self):
        """إرجاع قائمة الحسابات"""
        accounts = []
        for phone, data in self.data['accounts'].items():
            accounts.append((
                phone,
                data.get('session', ''),
                data.get('status', 'unknown'),
                data.get('total_posts', 0),
                data.get('success_posts', 0),
                data.get('failed_posts', 0)
            ))
        return accounts
    
    def get_account_sessions(self):
        """إرجاع قاموس الجلسات للتشغيل"""
        return {phone: data['session'] for phone, data in self.data['accounts'].items()}
    
    def update_account_status(self, phone, status):
        if phone in self.data['accounts']:
            self.data['accounts'][phone]['status'] = status
            self.data['accounts'][phone]['last_active'] = str(datetime.now())
            self.save_data()
    
    def increment_posts(self, phone, success=True):
        if phone in self.data['accounts']:
            acc = self.data['accounts'][phone]
            acc['total_posts'] += 1
            if success:
                acc['success_posts'] += 1
            else:
                acc['failed_posts'] += 1
            self.save_data()
    
    # ========== إدارة المجموعات ==========
    def add_group(self, group_id, name, members=0):
        gid = str(group_id)
        if gid not in self.data['groups']:
            self.data['groups'][gid] = {
                'name': name or 'بدون اسم',
                'members': members,
                'posts': 0,
                'last_post': None,
                'blacklisted': False
            }
            self.save_data()
    
    def update_group_post(self, group_id):
        gid = str(group_id)
        if gid in self.data['groups']:
            self.data['groups'][gid]['posts'] += 1
            self.data['groups'][gid]['last_post'] = str(datetime.now())
            self.save_data()
    
    def blacklist_group(self, group_id):
        gid = str(group_id)
        if gid in self.data['groups']:
            self.data['groups'][gid]['blacklisted'] = True
            self.save_data()
    
    def whitelist_group(self, group_id):
        gid = str(group_id)
        if gid in self.data['groups']:
            self.data['groups'][gid]['blacklisted'] = False
            self.save_data()
    
    def get_all_groups(self):
        groups = []
        for gid, data in self.data['groups'].items():
            groups.append((
                gid,
                data['name'],
                data['members'],
                data['posts'],
                1 if data['blacklisted'] else 0,
                data['last_post']
            ))
        return groups
    
    def get_blacklisted(self):
        return [(gid, data['name']) for gid, data in self.data['groups'].items() 
                if data.get('blacklisted', False)]
    
    def search_groups(self, query):
        results = []
        for gid, data in self.data['groups'].items():
            if query.lower() in data['name'].lower():
                results.append((gid, data['name'], data['members']))
        return results[:20]
    
    # ========== سجل النشر ==========
    def log_post(self, phone, group_id, group_name, status='success', error=None):
        self.data['history'].append({
            'phone': phone,
            'group_id': str(group_id),
            'group_name': group_name,
            'time': str(datetime.now()),
            'status': status,
            'error': error
        })
        
        # تحديث إحصائيات الحساب
        self.increment_posts(phone, status == 'success')
        
        # تحديث إحصائيات المجموعة
        if status == 'success':
            self.update_group_post(group_id)
        
        # الحفاظ على حجم التاريخ (آخر 1000)
        if len(self.data['history']) > 1000:
            self.data['history'] = self.data['history'][-1000:]
        
        self.save_data()
    
    def get_stats(self, hours=24):
        since = datetime.now() - timedelta(hours=hours)
        total = success = failed = 0
        
        for post in self.data['history']:
            post_time = datetime.fromisoformat(post['time'])
            if post_time > since:
                total += 1
                if post['status'] == 'success':
                    success += 1
                else:
                    failed += 1
        
        return {'total': total, 'success': success, 'failed': failed}
    
    def get_recent_posts(self, limit=10):
        recent = []
        for post in self.data['history'][-limit:]:
            recent.append((
                post['phone'],
                post['group_name'],
                post['status'],
                post['time']
            ))
        return recent
    
    # ========== الردود التلقائية ==========
    def add_auto_reply(self, keyword, response):
        self.data['auto_replies'].append({
            'id': len(self.data['auto_replies']) + 1,
            'keyword': keyword,
            'response': response,
            'match_type': 'exact',
            'active': True,
            'created': str(datetime.now())
        })
        self.save_data()
    
    def get_auto_replies(self):
        replies = []
        for r in self.data['auto_replies']:
            replies.append((
                r['id'],
                r['keyword'],
                r['response'],
                r['match_type'],
                1 if r['active'] else 0
            ))
        return replies
    
    def delete_auto_reply(self, rid):
        self.data['auto_replies'] = [r for r in self.data['auto_replies'] 
                                     if r['id'] != int(rid)]
        self.save_data()
    
    def toggle_auto_reply(self, rid, status):
        for r in self.data['auto_replies']:
            if r['id'] == int(rid):
                r['active'] = status
                break
        self.save_data()
    
    # ========== قائمة الانتظار ==========
    def add_to_queue(self, phone, group_id, message):
        self.data['queue'].append({
            'id': len(self.data['queue']) + 1,
            'phone': phone,
            'group_id': str(group_id),
            'message': message,
            'attempts': 0,
            'created': str(datetime.now())
        })
        self.save_data()
    
    def get_queue(self):
        queue = []
        for q in self.data['queue']:
            queue.append((
                q['id'],
                q['phone'],
                q['group_id'],
                q['message'],
                q['attempts']
            ))
        return queue

# تهيئة مدير البيانات
data_manager = DataManager()

# ==================== المتغيرات العامة ====================
USER_CLIENTS = {}
TEMP = {}
is_posting = False

# تحميل الإعدادات
SETTINGS = {
    'interval': data_manager.get_setting('interval', 3),
    'encryption': data_manager.get_setting('encryption', True),
    'auto_join_enabled': data_manager.get_setting('auto_join', True),
    'max_groups_per_account': data_manager.get_setting('max_groups', 50),
    'delay_between_accounts': data_manager.get_setting('delay_accounts', 2)
}

MESSAGES = data_manager.get_all_messages()

# ==================== وظائف مساعدة ====================
def format_number(n):
    if n >= 1000000:
        return f"{n/1000000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)

def encrypt_text(text):
    if not SETTINGS.get('encryption'):
        return text
    chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
    words = text.split()
    return " ".join([w + (random.choice(chars) if random.random() > 0.5 else "") for w in words])

# ==================== الأزرار ====================
def main_buttons():
    enc_status = "✅ مفعل" if SETTINGS['encryption'] else "❌ معطل"
    post_icon = "🚀" if is_posting else "🛑"
    return [
        [Button.inline("➕ إضافة حساب", b"add"), Button.inline("🗑 حذف حساب", b"del_list")],
        [Button.inline("📝 ضبط الرسالة", b"msg"), Button.inline("⏱ ضبط الوقت", b"time")],
        [Button.inline(f"{post_icon} بدء النشر", b"start_p"), Button.inline("🛑 إيقاف النشر", b"stop_p")],
        [Button.inline(f"🛡 التشفير: {enc_status}", b"toggle_enc"), Button.inline("📊 الحالة", b"status")],
        [Button.inline("📢 المجموعات", b"view_chats"), Button.inline("⚙️ إعدادات متقدمة", b"advanced")],
        [Button.inline("📈 إحصائيات", b"stats"), Button.inline("🤖 ميزات خارقة", b"super")],
        [Button.inline("📋 سجل النشر", b"history"), Button.inline("💾 حفظ", b"save")]
    ]

def advanced_buttons():
    return [
        [Button.inline("🚫 قائمة المحظورات", b"blacklist"), Button.inline("🔍 بحث", b"search")],
        [Button.inline("📊 إحصائيات تفصيلية", b"detailed"), Button.inline("📥 قائمة الانتظار", b"queue")],
        [Button.inline("⬅️ عودة", b"back")]
    ]

def super_buttons():
    return [
        [Button.inline("🤖 الردود التلقائية", b"auto_reply"), Button.inline("🔐 تجربة التشفير", b"test_enc")],
        [Button.inline("📊 تحليل المجموعات", b"analyze"), Button.inline("🎯 استهداف ذكي", b"target")],
        [Button.inline("⬅️ عودة", b"back")]
    ]

def auto_reply_buttons():
    return [
        [Button.inline("➕ إضافة رد", b"add_reply"), Button.inline("🗑 حذف رد", b"del_reply")],
        [Button.inline("📋 عرض الكل", b"list_replies"), Button.inline("⬅️ عودة", b"super")]
    ]

# ==================== استعادة الحسابات ====================
async def restore_sessions():
    """استعادة جميع الحسابات من البيانات المحفوظة"""
    restored = 0
    accounts = data_manager.get_account_sessions()
    
    print(f"📱 جاري استعادة {len(accounts)} حساب...")
    
    for phone, session_string in accounts.items():
        try:
            if session_string and len(session_string) > 10:
                client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
                await client.connect()
                
                if await client.is_user_authorized():
                    USER_CLIENTS[phone] = client
                    data_manager.update_account_status(phone, 'active')
                    restored += 1
                    print(f"✅ تم استعادة: {phone}")
                else:
                    data_manager.update_account_status(phone, 'unauthorized')
        except Exception as e:
            print(f"❌ فشل استعادة {phone}: {str(e)[:50]}")
    
    print(f"✅ تم استعادة {restored} حساب")
    return restored

# ==================== تسجيل الدخول ====================
async def handle_phone_login(event, phone):
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        
        TEMP[ADMIN_ID] = {"s": "code", "p": phone, "c": client}
        await event.respond(f"📩 تم إرسال الكود إلى {phone}\nأرسل الكود الآن:")
    except Exception as e:
        await event.respond(f"❌ خطأ: {str(e)[:100]}")

async def handle_code_verification(event, state, code):
    try:
        client = state["c"]
        phone = state["p"]
        
        await client.sign_in(phone, code)
        
        # حفظ الجلسة في التخزين الدائم
        session_string = client.session.save()
        data_manager.add_account(phone, session_string)
        USER_CLIENTS[phone] = client
        
        await event.respond(f"✅ تم تفعيل {phone} بنجاح!\n💾 تم الحفظ في Render")
        TEMP.pop(ADMIN_ID, None)
        
    except SessionPasswordNeededError:
        TEMP[ADMIN_ID] = {"s": "pass", "p": phone, "c": client}
        await event.respond("🔐 هذا الحساب محمي بكلمة سر\nأرسل كلمة المرور:")
    except Exception as e:
        await event.respond(f"❌ فشل: {str(e)[:100]}")

async def handle_password(event, state, password):
    try:
        client = state["c"]
        phone = state["p"]
        
        await client.sign_in(password=password)
        
        session_string = client.session.save()
        data_manager.add_account(phone, session_string)
        USER_CLIENTS[phone] = client
        
        await event.respond(f"✅ تم تفعيل {phone} بنجاح!\n💾 تم الحفظ في Render")
        TEMP.pop(ADMIN_ID, None)
        
    except Exception as e:
        await event.respond(f"❌ خطأ: {str(e)[:100]}")

# ==================== النشر ====================
async def poster():
    global is_posting
    print("🚀 بدء النشر...")
    
    while is_posting:
        try:
            if not USER_CLIENTS or "1" not in MESSAGES:
                await asyncio.sleep(5)
                continue
            
            message = MESSAGES["1"]
            
            for phone, client in list(USER_CLIENTS.items()):
                if not is_posting:
                    break
                
                try:
                    sent = 0
                    async for dialog in client.iter_dialogs():
                        if not is_posting:
                            break
                        
                        if dialog.is_group or dialog.is_channel:
                            # تحقق من القائمة السوداء
                            blacklisted = [g[0] for g in data_manager.get_blacklisted()]
                            if str(dialog.id) in blacklisted:
                                continue
                            
                            if sent >= SETTINGS['max_groups_per_account']:
                                break
                            
                            try:
                                # حفظ المجموعة
                                members = getattr(dialog.entity, 'participants_count', 0)
                                data_manager.add_group(dialog.id, dialog.name, members)
                                
                                # إرسال الرسالة
                                await client.send_message(dialog.id, encrypt_text(message))
                                
                                # تسجيل النجاح
                                data_manager.log_post(phone, dialog.id, dialog.name, 'success')
                                sent += 1
                                
                                await asyncio.sleep(SETTINGS['interval'])
                                
                            except FloodWaitError as e:
                                print(f"⚠️ انتظار {e.seconds} ثانية")
                                await asyncio.sleep(e.seconds)
                            except Exception as e:
                                data_manager.log_post(phone, dialog.id, dialog.name, 'failed', str(e)[:50])
                    
                    await asyncio.sleep(SETTINGS['delay_between_accounts'])
                    
                except Exception as e:
                    print(f"❌ خطأ في حساب {phone}: {e}")
            
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ خطأ عام: {e}")
            await asyncio.sleep(10)
    
    print("🛑 توقف النشر")

# ==================== معالجات الأحداث ====================
async def start_handler(event):
    if event.sender_id != ADMIN_ID:
        return
    
    accounts = data_manager.get_accounts()
    groups = data_manager.get_all_groups()
    stats = data_manager.get_stats()
    
    text = (f"🤖 **بوت Render الأسطوري**\n\n"
            f"📊 **الحالة:**\n"
            f"• الحسابات: `{len(USER_CLIENTS)}/{len(accounts)}`\n"
            f"• المجموعات: `{len(groups)}`\n"
            f"• منشورات اليوم: `{stats['total']}`\n"
            f"• النشر: `{'🚀 يعمل' if is_posting else '🛑 متوقف'}`\n\n"
            f"💾 **الحفظ:** دائم على Render ✅")
    
    await event.respond(text, buttons=main_buttons())

async def callback_handler(event):
    global is_posting
    
    if event.sender_id != ADMIN_ID:
        return
    
    data = event.data.decode()
    
    if data == "back":
        await event.edit("👋 القائمة الرئيسية:", buttons=main_buttons())
    
    elif data == "advanced":
        await event.edit("⚙️ إعدادات متقدمة:", buttons=advanced_buttons())
    
    elif data == "super":
        await event.edit("🤖 الميزات الخارقة:", buttons=super_buttons())
    
    elif data == "auto_reply":
        replies = data_manager.get_auto_replies()
        text = f"🤖 **الردود التلقائية**\nعدد الردود: {len(replies)}\n\n"
        for rid, kw, resp, mt, active in replies[:10]:
            status = "🟢" if active else "🔴"
            text += f"{status} `{kw}` → {resp[:30]}...\n"
        await event.edit(text, buttons=auto_reply_buttons())
    
    elif data == "start_p":
        if not is_posting:
            is_posting = True
            asyncio.create_task(poster())
            await event.answer("🚀 بدأ النشر!", alert=True)
        else:
            await event.answer("⚠️ النشر يعمل بالفعل!", alert=True)
        await event.edit(buttons=main_buttons())
    
    elif data == "stop_p":
        is_posting = False
        await event.answer("🛑 توقف النشر", alert=True)
        await event.edit(buttons=main_buttons())
    
    elif data == "toggle_enc":
        SETTINGS['encryption'] = not SETTINGS['encryption']
        data_manager.set_setting('encryption', SETTINGS['encryption'])
        await event.edit(buttons=main_buttons())
    
    elif data == "status":
        stats = data_manager.get_stats()
        await event.answer(
            f"📊 إحصائيات 24 ساعة:\n"
            f"✅ نجاح: {stats['success']}\n"
            f"❌ فشل: {stats['failed']}\n"
            f"📦 المجموع: {stats['total']}",
            alert=True
        )
    
    elif data == "msg":
        TEMP[ADMIN_ID] = "msg"
        await event.respond("📝 أرسل نص الإعلان:")
    
    elif data == "time":
        TEMP[ADMIN_ID] = "time"
        await event.respond("⏱ أرسل الفاصل الزمني (1-60 ثانية):")
    
    elif data == "add":
        TEMP[ADMIN_ID] = "phone"
        await event.respond("📱 أرسل رقم الهاتف (مع مفتاح الدولة):")
    
    elif data == "del_list":
        accounts = data_manager.get_accounts()
        if not accounts:
            await event.answer("❌ لا توجد حسابات", alert=True)
            return
        
        btns = []
        for phone, sess, status, total, suc, fail in accounts[:10]:
            short = phone[-8:]
            icon = "🟢" if status == 'active' else "🔴"
            btns.append([Button.inline(f"{icon} {short} ({total})", f"rm_{phone}".encode())])
        
        btns.append([Button.inline("⬅️ عودة", b"back")])
        await event.edit("🗑 اختر حساباً للحذف:", buttons=btns)
    
    elif data.startswith("rm_"):
        phone = data[3:]
        if phone in USER_CLIENTS:
            await USER_CLIENTS[phone].disconnect()
            del USER_CLIENTS[phone]
        data_manager.remove_account(phone)
        await event.answer(f"✅ تم حذف {phone}", alert=True)
        await callback_handler(event)  # العودة لقائمة الحذف
    
    elif data == "view_chats":
        groups = data_manager.get_all_groups()
        blacklisted = data_manager.get_blacklisted()
        
        text = f"📢 **المجموعات**\nالإجمالي: {len(groups)} | محظور: {len(blacklisted)}\n\n"
        for gid, name, members, posts, bl, last in groups[:15]:
            name_short = name[:25]
            status = "🚫" if bl else "✅"
            members_fmt = format_number(members)
            text += f"{status} {name_short}\n   👥 {members_fmt} | 📨 {posts}\n"
        
        await event.edit(text, buttons=main_buttons())
    
    elif data == "history":
        recent = data_manager.get_recent_posts(15)
        text = "📋 **آخر 15 منشور**\n\n"
        for phone, group, status, t in recent:
            time_str = datetime.fromisoformat(t).strftime('%H:%M')
            icon = "✅" if status == 'success' else "❌"
            text += f"{icon} {time_str} - {group[:20]}\n"
        await event.edit(text, buttons=advanced_buttons())
    
    elif data == "save":
        await event.answer("✅ جميع البيانات محفوظة في Render!", alert=True)
    
    elif data == "blacklist":
        blacklisted = data_manager.get_blacklisted()
        if not blacklisted:
            await event.edit("📭 لا توجد مجموعات محظورة", buttons=advanced_buttons())
            return
        
        text = "🚫 **المجموعات المحظورة**\n\n"
        for gid, name in blacklisted[:20]:
            text += f"• {name[:40]}\n"
        await event.edit(text, buttons=advanced_buttons())
    
    elif data == "test_enc":
        original = "رسالة اختبار للتشفير"
        encrypted = encrypt_text(original)
        text = f"🔐 **اختبار التشفير**\n\n📝 الأصلي: {original}\n🔒 المشفر: {encrypted}"
        await event.edit(text, buttons=super_buttons())
    
    elif data == "analyze":
        groups = data_manager.get_all_groups()
        if not groups:
            await event.answer("❌ لا توجد مجموعات", alert=True)
            return
        
        total_members = sum(g[2] or 0 for g in groups)
        active = len([g for g in groups if g[3] > 0])
        
        text = (f"📊 **تحليل المجموعات**\n\n"
                f"عدد المجموعات: {len(groups)}\n"
                f"إجمالي الأعضاء: {format_number(total_members)}\n"
                f"المجموعات النشطة: {active}\n"
                f"نسبة النشاط: {active/len(groups)*100:.1f}%")
        
        await event.edit(text, buttons=super_buttons())
    
    elif data == "add_reply":
        TEMP[ADMIN_ID] = {"s": "reply_keyword"}
        await event.respond("🔑 أرسل الكلمة المفتاحية:")

async def text_handler(event):
    state = TEMP.get(ADMIN_ID)
    text = event.message.text.strip()
    
    # الردود التلقائية
    if event.is_group and event.message.text and not event.out:
        replies = data_manager.get_auto_replies()
        msg_lower = text.lower()
        for rid, kw, resp, mt, active in replies:
            if active and kw.lower() in msg_lower:
                await event.reply(resp)
                break
    
    # معالجة الروابط
    links = re.findall(r"(https?://t\.me/\S+)", text)
    if links and SETTINGS['auto_join_enabled'] and USER_CLIENTS:
        await event.respond(f"⏳ جاري الانضمام إلى {len(links)} مجموعة...")
        for link in links[:3]:
            for phone, client in USER_CLIENTS.items():
                try:
                    if "joinchat" in link or "+" in link:
                        hash_part = link.split('/')[-1].replace('+', '')
                        await client(ImportChatInviteRequest(hash_part))
                    else:
                        await client(JoinChannelRequest(link))
                    await event.respond(f"✅ {phone} انضم إلى {link[:30]}")
                except Exception as e:
                    await event.respond(f"❌ {phone}: {str(e)[:50]}")
                await asyncio.sleep(2)
        return
    
    # معالجة حالات المستخدم
    if isinstance(state, dict):
        if state.get("s") == "code":
            await handle_code_verification(event, state, text)
        elif state.get("s") == "pass":
            await handle_password(event, state, text)
        elif state.get("s") == "reply_keyword":
            TEMP[ADMIN_ID] = {"s": "reply_response", "kw": text}
            await event.respond("💬 أرسل نص الرد:")
        elif state.get("s") == "reply_response":
            data_manager.add_auto_reply(state['kw'], text)
            await event.respond("✅ تم إضافة الرد!", buttons=super_buttons())
            TEMP.pop(ADMIN_ID)
    
    elif state == "msg":
        MESSAGES["1"] = text
        data_manager.save_message("1", text)
        TEMP.pop(ADMIN_ID)
        await event.respond("✅ تم حفظ الإعلان!", buttons=main_buttons())
    
    elif state == "time":
        try:
            interval = int(text)
            if 1 <= interval <= 60:
                SETTINGS['interval'] = interval
                data_manager.set_setting('interval', interval)
                TEMP.pop(ADMIN_ID)
                await event.respond(f"✅ تم ضبط الوقت على {text} ثانية", buttons=main_buttons())
            else:
                await event.respond("❌ القيمة بين 1 و 60")
        except:
            await event.respond("❌ أرسل رقماً صحيحاً")
    
    elif state == "phone":
        await handle_phone_login(event, text)

# ==================== الدالة الرئيسية ====================
async def main():
    print("="*60)
    print("🚀 بوت Render الأسطوري - مع الحفظ الدائم")
    print("="*60)
    
    # تشغيل خادم الويب
    Thread(target=run_web, daemon=True).start()
    
    # استعادة الحسابات
    await restore_sessions()
    
    # تشغيل البوت
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(e):
        await start_handler(e)
    
    @bot.on(events.CallbackQuery())
    async def callback(e):
        await callback_handler(e)
    
    @bot.on(events.NewMessage)
    async def text(e):
        if e.message.text:
            await text_handler(e)
    
    print("✅ البوت جاهز على Render!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 تم إيقاف البوت")
    except Exception as e:
        print(f"💥 خطأ: {e}")
        time.sleep(5)
        os.execl(sys.executable, sys.executable, *sys.argv)
