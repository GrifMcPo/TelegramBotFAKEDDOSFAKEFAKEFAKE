import asyncio
import os
import sys
import json
import base64
import logging
import re
import requests
import ipaddress
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8857252828"))

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LOGS_FILE = "logs.json"
BLACKLIST_FILE = "blacklist.json"
REPO = "GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE"
BRANCH = "main"

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

# ========== ЧЕРНЫЙ СПИСОК ==========
def load_blacklist():
    try:
        if os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_blacklist_local(blacklist):
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def save_blacklist_to_github():
    try:
        if not GITHUB_TOKEN:
            return False
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        url = f"https://api.github.com/repos/{REPO}/contents/{BLACKLIST_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        existing = requests.get(url, headers=headers)
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {"message": f"📊 Update blacklist {get_msk_time()}", "content": encoded, "branch": BRANCH}
        if sha:
            payload["sha"] = sha
        response = requests.put(url, headers=headers, json=payload)
        return response.status_code in [200, 201]
    except:
        return False

def add_to_blacklist(user_id, reason, admin_id):
    blacklist = load_blacklist()
    blacklist[str(user_id)] = {
        "reason": reason,
        "added_by": admin_id,
        "added_at": get_msk_time()
    }
    save_blacklist_local(blacklist)
    asyncio.create_task(async_save_blacklist())
    return True

def remove_from_blacklist(user_id):
    blacklist = load_blacklist()
    if str(user_id) in blacklist:
        del blacklist[str(user_id)]
        save_blacklist_local(blacklist)
        asyncio.create_task(async_save_blacklist())
        return True
    return False

def is_blacklisted(user_id):
    blacklist = load_blacklist()
    return str(user_id) in blacklist

def get_blacklist_reason(user_id):
    blacklist = load_blacklist()
    return blacklist.get(str(user_id), {}).get("reason", "Не указана")

def get_blacklist_list():
    blacklist = load_blacklist()
    return blacklist

async def async_save_blacklist():
    await asyncio.to_thread(save_blacklist_to_github)

# ========== ЛОГИ ==========
def save_log_local(log_entry):
    try:
        logs = []
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        logs.append(log_entry)
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def save_to_github():
    try:
        if not GITHUB_TOKEN:
            return False
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        url = f"https://api.github.com/repos/{REPO}/contents/{LOGS_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        existing = requests.get(url, headers=headers)
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {"message": f"📊 Update logs {get_msk_time()}", "content": encoded, "branch": BRANCH}
        if sha:
            payload["sha"] = sha
        response = requests.put(url, headers=headers, json=payload)
        return response.status_code in [200, 201]
    except:
        return False

def save_log(log_entry):
    save_log_local(log_entry)
    asyncio.create_task(async_save_to_github())

async def async_save_to_github():
    await asyncio.to_thread(save_to_github)

# ========== КОМАНДЫ ДЛЯ ЧЕРНОГО СПИСКА ==========
@dp.message(Command("block"))
async def block_user(message: types.Message):
    """/block [ID] [причина] — добавить в черный список"""
    user_id = message.from_user.id
    
    # Только админ
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ /block [ID] [причина]\nПример: /block 123456789 Спам")
        return
    
    target_id = args[1]
    reason = args[2]
    
    if add_to_blacklist(target_id, reason, user_id):
        await message.answer(f"✅ Пользователь {target_id} добавлен в черный список!\n📌 Причина: {reason}")
    else:
        await message.answer("❌ Ошибка при добавлении в черный список")

@dp.message(Command("unblock"))
async def unblock_user(message: types.Message):
    """/unblock [ID] — удалить из черного списка"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ /unblock [ID]\nПример: /unblock 123456789")
        return
    
    target_id = args[1]
    
    if remove_from_blacklist(target_id):
        await message.answer(f"✅ Пользователь {target_id} удален из черного списка!")
    else:
        await message.answer(f"❌ Пользователь {target_id} не найден в черном списке")

@dp.message(Command("blacklist"))
async def show_blacklist(message: types.Message):
    """/blacklist — показать черный список"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return
    
    blacklist = get_blacklist_list()
    
    if not blacklist:
        await message.answer("📭 Черный список пуст")
        return
    
    text = "⛔ ЧЕРНЫЙ СПИСОК:\n\n"
    for uid, data in blacklist.items():
        text += f"🆔 {uid}\n📌 {data.get('reason', 'Без причины')}\n👤 Добавил: {data.get('added_by', 'Неизвестно')}\n🕐 {data.get('added_at', 'Неизвестно')}\n━━━━━━━━━━━━━━\n"
    
    await message.answer(text)

# ========== ОСТАЛЬНЫЕ КОМАНДЫ ==========
# ... (все остальные команды из предыдущей версии)
# /start, /help, /whois ip, /whois number, /stats

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🔥 БОТ ЗАПУЩЕН!")
    print("📌 Команды: /start, /help, /whois, /stats")
    print("📌 Админ: /block, /unblock, /blacklist")
    print("=" * 60)
    
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        if "Conflict" in str(e):
            print("⚠️ Конфликт! Переподключаемся...")
            await asyncio.sleep(5)
            await dp.start_polling(bot)
        else:
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Сохраняем логи...")
        save_to_github()
        save_blacklist_to_github()
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
