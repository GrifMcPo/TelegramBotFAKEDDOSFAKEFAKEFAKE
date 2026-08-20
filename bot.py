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
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # ВАЖНО!

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LOGS_FILE = "logs.json"
REPO = "GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE"
BRANCH = "main"

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

# ========== РАБОТА С GITHUB ==========
def save_to_github(data):
    """Сохраняет логи в репозиторий через GitHub API"""
    try:
        if not GITHUB_TOKEN:
            print("⚠️ НЕТ GITHUB_TOKEN! Логи сохраняются локально.")
            return False
            
        url = f"https://api.github.com/repos/{REPO}/contents/{LOGS_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Получаем текущий файл (если есть)
        existing = requests.get(url, headers=headers)
        sha = None
        if existing.status_code == 200:
            sha = existing.json().get("sha")
        
        # Читаем локальный файл
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Добавляем новую запись
        logs.append({
            "command": "тест",
            "user_id": 0,
            "username": "system",
            "time": get_msk_time()
        })
        
        # Сохраняем
        content = json.dumps(logs, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": f"📊 Update logs {get_msk_time()}",
            "content": encoded,
            "branch": BRANCH
        }
        if sha:
            payload["sha"] = sha
        
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            print(f"✅ Файл {LOGS_FILE} сохранён в GitHub!")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def save_log(log_entry):
    """Сохраняет лог локально и в GitHub"""
    try:
        # Локально
        logs = []
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        logs.append(log_entry)
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        print(f"✅ Локально сохранён: {log_entry.get('command')}")
        
        # В GitHub
        if GITHUB_TOKEN:
            return save_to_github(log_entry)
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    await save_log({
        "command": "/start",
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "time": get_msk_time()
    })
    
    await message.answer("🔥 БОТ РАБОТАЕТ!\n💡 /help - список команд")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📚 КОМАНДЫ:\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/whois ip [IP] - Пробив IP\n"
        "/whois number [НОМЕР] - Пробив номера"
    )

@dp.message(Command("whois"))
async def whois_command(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ /whois ip [IP] или /whois number [НОМЕР]")
        return
    
    command_type = args[1].lower()
    target = args[2]
    
    if command_type == "ip":
        await save_log({
            "command": f"/whois ip {target}",
            "user_id": message.from_user.id,
            "username": message.from_user.username or "Нет",
            "target": target,
            "time": get_msk_time()
        })
        await message.answer(f"✅ Пробив IP {target} выполнен!")
    elif command_type == "number":
        await save_log({
            "command": f"/whois number {target}",
            "user_id": message.from_user.id,
            "username": message.from_user.username or "Нет",
            "target": target,
            "time": get_msk_time()
        })
        await message.answer(f"✅ Пробив номера {target} выполнен!")

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await message.answer("📊 Статистика: бот работает!")

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🔥 БОТ ЗАПУЩЕН!")
    print(f"📌 GitHub токен: {'ЕСТЬ ✅' if GITHUB_TOKEN else 'НЕТ ❌'}")
    print("📌 Файл будет сохранён в репозиторий!")
    print("=" * 60)
    
    # СОЗДАЁМ ФАЙЛ ПРЯМО СЕЙЧАС!
    if GITHUB_TOKEN:
        save_to_github({})
        print("✅ Файл logs.json создан в репозитории!")
    else:
        with open(LOGS_FILE, 'w') as f:
            json.dump([], f)
        print("✅ Файл logs.json создан локально!")
    
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
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
