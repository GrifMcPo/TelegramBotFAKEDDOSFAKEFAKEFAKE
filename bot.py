import asyncio
import os
import sys
import json
import logging
import re
import requests
import ipaddress
import phonenumbers
from phonenumbers import carrier, geocoder, timezone, number_type
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BusinessConnection
from aiogram import F
import aioheader # Добавлено: библиотека для запросов к API

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN = 8308522569

# НАСТРОЙКИ SUPABASE (берутся из .env или GitHub Secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не найдены Токен Бота или Ключи Supabase!")
    print(f"Токен: {'Есть' if BOT_TOKEN else 'Нет'}")
    print(f"URL: {'Есть' if SUPABASE_URL else 'Нет'}")
    print(f"Key: {'Есть' if SUPABASE_KEY else 'Нет'}")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LOGS_FILE = "data/logs.json"
BLACKLIST_FILE = "data/blacklist.json"
business_connections = {}
blocked_notified = {}

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

# ========== ЧЕРНЫЙ СПИСОК (без изменений) ==========
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

def add_to_blacklist(user_id, reason, admin_id, time_minutes=0):
    blacklist = load_blacklist()
    expires_at = None
    if time_minutes > 0:
        expires_at = (datetime.now() + timedelta(minutes=time_minutes)).isoformat()
    
    blacklist[str(user_id)] = {
        "reason": reason,
        "added_by": admin_id,
        "added_at": get_msk_time(),
        "expires_at": expires_at
    }
    save_blacklist_local(blacklist)
    if str(user_id) in blocked_notified:
        del blocked_notified[str(user_id)]
    return True

def remove_from_blacklist(user_id):
    blacklist = load_blacklist()
    if str(user_id) in blacklist:
        del blacklist[str(user_id)]
        save_blacklist_local(blacklist)
        if str(user_id) in blocked_notified:
            del blocked_notified[str(user_id)]
        return True
    return False

def is_blacklisted(user_id):
    blacklist = load_blacklist()
    if str(user_id) not in blacklist:
        return False
    
    data = blacklist[str(user_id)]
    if data.get("expires_at"):
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() > expires:
            del blacklist[str(user_id)]
            save_blacklist_local(blacklist)
            if str(user_id) in blocked_notified:
                del blocked_notified[str(user_id)]
            return False
    
    return True

def get_blacklist_reason(user_id):
    blacklist = load_blacklist()
    data = blacklist.get(str(user_id), {})
    reason = data.get("reason", "Не указана")
    expires = data.get("expires_at")
    if expires:
        expires_dt = datetime.fromisoformat(expires)
        time_left = expires_dt - datetime.now()
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        if time_left.days > 0:
            time_str = f"{time_left.days}д {hours}ч"
        elif hours > 0:
            time_str = f"{hours}ч {minutes}м"
        else:
            time_str = f"{minutes}м"
        reason += f" (осталось: {time_str})"
    
    return reason

def is_admin(user_id):
    return user_id == MAIN_ADMIN

# ========== ЛОГИ (без изменений) ==========
def save_log(log_entry):
    try:
        os.makedirs(os.path.dirname(LOGS_FILE), exist_ok=True)
        logs = []
        if os.path.exists(LOGS_FILE):
            try:
                with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        logs = json.loads(content)
                        if not isinstance(logs, list):
                            logs = []
            except:
                logs = []
        
        logs.append(log_entry)
        
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения лога: {e}")
        return False

def get_logs_for_user(identifier):
    try:
        if not os.path.exists(LOGS_FILE):
            return []
        
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            all_logs = json.load(f)
        
        is_id = identifier.isdigit()
        five_days_ago = (datetime.utcnow() + timedelta(hours=3) - timedelta(days=5))
        
        filtered_logs = []
        for log in all_logs:
            log_time_str = log.get('time', '')
            if log_time_str:
                try:
                    log_time = datetime.strptime(log_time_str, '%d.%m.%Y %H:%M:%S')
                    if log_time < five_days_ago:
                        continue
                except:
                    pass
            
            if is_id:
                if str(log.get('user_id', '')) == identifier:
                    filtered_logs.append(log)
            else:
                username = log.get('username', '').lower()
                identifier_clean = identifier.lower().replace('@', '')
                if identifier_clean in username:
                    filtered_logs.append(log)
        
        return filtered_logs
    except Exception as e:
        print(f"❌ Ошибка получения логов: {e}")
        return []

def get_all_users():
    try:
        if not os.path.exists(LOGS_FILE):
            return {}
        
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            all_logs = json.load(f)
        
        users = {}
        for log in all_logs:
            user_id = log.get('user_id')
            username = log.get('username', 'Нет')
            full_name = log.get('full_name', 'Нет')
            if user_id:
                users[str(user_id)] = {
                    'username': username,
                    'full_name': full_name
                }
        
        return users
    except Exception as e:
        print(f"❌ Ошибка получения списка пользователей: {e}")
        return {}

# ========== ВЫПОЛНЕНИЕ КОМАНД (без изменений) ==========
def execute_command(command):
    command = command.strip()
    
    if command == '/idlist':
        users = get_all_users()
        if not users:
            return "📊 Нет пользователей в логах"
        
        result = "👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n\n"
        for uid, data in users.items():
            username = data.get('username', 'Нет')
            full_name = data.get('full_name', 'Нет')
            result += f"🆔 {uid}\n"
            if username != 'Нет':
                result += f"👤 @{username}\n"
            if full_name != 'Нет':
                result += f"📛 {full_name}\n"
            result += "─" * 20 + "\n"
        return result
    
    if command == '/stats':
        try:
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            users = set(l.get('user_id') for l in logs)
            probes = len([l for l in logs if 'whois' in l.get('command', '').lower()])
            return f"📊 СТАТИСТИКА\n\n👤 Пользователей: {len(users)}\n📝 Команд: {len(logs)}\n🔍 Пробивов: {probes}\n🕐 Время: {get_msk_time()}"
        except:
            return "📊 Статистика временно недоступна"
    
    if command.startswith('/logs '):
        identifier = command[6:].strip()
        logs = get_logs_for_user(identifier)
        
        if not logs:
            return f"❌ Логи не найдены для {identifier}"
        
        total_commands = len(logs)
        probes = len([l for l in logs if 'whois' in l.get('command', '').lower()])
        
        result = f"📊 ЛОГИ ДЛЯ: {identifier}\n"
        result += f"📝 Всего команд: {total_commands}\n"
        result += f"🔍 Пробивов: {probes}\n"
        result += f"🕐 За последние 5 дней\n\n"
        result += "─" * 30 + "\n\n"
        
        for log in logs[-50:]:
            command_text = log.get('command', 'Неизвестно')
            time = log.get('time', '')
            result += f"🕐 {time}\n"
            result += f"📝 {command_text}\n"
            if log.get('target'):
                result += f"🎯 {log['target']}\n"
            result += "─" * 20 + "\n"
        return result
    
    if command == '/help':
        return """📚 ДОСТУПНЫЕ КОМАНДЫ

📊 СТАТИСТИКА:
/idlist - Список всех пользователей
/stats - Общая статистика
/logs [ID/@username] - Логи пользователя

⚡ УПРАВЛЕНИЕ:
/ban [ID] [время] [причина]
/unban [ID] [причина]

💡 ТЕСТ:
/ping - Проверка соединения
/time - Текущее время"""

    if command == '/ping':
        return f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}"
    
    if command == '/time':
        return f"🕐 МСК: {get_msk_time()}"
    
    if command.startswith('/ban '):
        parts = command.split(maxsplit=3)
        if len(parts) < 3:
            return "❌ /ban [ID] [время в минутах] [причина]"
        
        target_id = parts[1]
        try:
            time_minutes = int(parts[2])
        except:
            time_minutes = 60
        reason = parts[3] if len(parts) > 3 else "Без причины"
        
        add_to_blacklist(target_id, reason, MAIN_ADMIN, time_minutes)
        
        save_log({
            "command": f"/ban {target_id}",
            "user_id": MAIN_ADMIN,
            "username": "RCON",
            "full_name": "RCON Admin",
            "target": target_id,
            "reason": reason,
            "time_minutes": time_minutes,
            "time": get_msk_time()
        })
        
        return f"✅ {target_id} Был успешно забанен в боте!\n📌 Причина: {reason}\n⏱ Время: {time_minutes} минут"
    
    if command.startswith('/unban '):
        parts = command.split(maxsplit=2)
        if len(parts) < 2:
            return "❌ /unban [ID] [причина]"
        
        target_id = parts[1]
        reason = parts[2] if len(parts) > 2 else "Без причины"
        
        if remove_from_blacklist(target_id):
            save_log({
                "command": f"/unban {target_id}",
                "user_id": MAIN_ADMIN,
                "username": "RCON",
                "full_name": "RCON Admin",
                "target": target_id,
                "reason": reason,
                "time": get_msk_time()
            })
            return f"✅ {target_id} был разбанен в боте!\n📌 Причина: {reason}"
        else:
            return f"❌ Пользователь {target_id} не найден в черном списке"
    
    return f"❌ Неизвестная команда: {command}\nВведите /help для списка команд"

# ========== НОВАЯ ЛОГИКА SUPABASE ==========
async def fetch_commands(session):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json"
    }
    params = {"select": "*", "order": "created_at.asc"}
    
    async with session.get(f"{SUPABASE_URL}/rest/v1/commands", headers=headers, params=params) as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            text = await resp.text()
            print(f"❌ [Supabase Fetch] Status: {resp.status}, Body: {text}")
            return []

async def insert_response(session, cmd_id, result, time_str):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "response_id": cmd_id,
        "result": str(result),
        "time": time_str
    }
    async with session.post(f"{SUPABASE_URL}/rest/v1/responses", headers=headers, json=payload) as resp:
        if resp.status != 201:
            print(f"❌ [Supabase Insert] Failed: {await resp.text()}")

# ========== РАБОЧИЙ ЦИКЛ САЙТ-БОТ ==========
async def supabase_worker():
    print("🟢 Worker запущен. Ожидание команд от сайта...")
    async with aiohttp.ClientSession() as session:
        while True:
            commands = await fetch_commands(session)
            
            for cmd in commands:
                cmd_id = cmd.get('id')
                text = cmd.get('command', '').strip()
                
                if text and cmd_id:
                    print(f"🌐 Получена команда с сайта ID:{cmd_id}: {text}")
                    
                    # Выполняем вашу стандартную функцию
                    result = execute_command(text)
                    
                    # Записываем ответ в таблицу responses
                    await insert_response(session, cmd_id, result, get_msk_time())
                    print(f"✅ Ответ записан для ID: {cmd_id}")
            
            await asyncio.sleep(3)

# ========== ОБРАБОТЧИКИ TELEGRAM (БЕЗ ИЗМЕНЕНИЙ) ==========
@dp.message(Command("start"))
async def start(message: types.Message): ... # Весь ваш код handlers остается прежним
@dp.message(Command("help")): ...
@dp.message(Command("ping")): ...
@dp.message(Command("time")): ...
@dp.message(Command("info")): ...
@dp.message(Command("stats")): ...
@dp.message(Command("idlist")): ...
@dp.message(Command("logs")): ...
@dp.message(Command("whois")): ...
@dp.message(Command("ban")): ...
@dp.message(Command("unban")): ...
@dp.callback_query(): ...
# Функции probe_ip, analyze_results, show_animation тоже остаются без изменений!

# ВАЖНО: Убедитесь, что функции handle_business_message используют те же пути к LOGS_FILE и BLACKLIST_FILE

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🔥 БОТ ЗАПУЩЕН (Hybrid Mode)")
    print(f"👤 АДМИН: {MAIN_ADMIN}")
    print(f"🌐 Supabase: {SUPABASE_URL}")
    print("=" * 60)
    
    os.makedirs('data', exist_ok=True)
    for file in [LOGS_FILE, BLACKLIST_FILE]:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                if file == BLACKLIST_FILE: json.dump({}, f)
                else: json.dump([], f)

    # Запускаем одновременно и Телеграм, и опрос базы
    worker_task = asyncio.create_task(supabase_worker())
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    await asyncio.gather(worker_task, polling_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Фатальная ошибка: {e}")
