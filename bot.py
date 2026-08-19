import asyncio
import os
import sys
import logging
import re
import requests
import random
import json
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types.business_connection import BusinessConnection
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ФАЙЛЫ ==========
USERS_FILE = "users.json"
STATS_FILE = "stats.json"

# ========== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ ==========
def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"✅ Загружено {len(data)} пользователей из users.json")
                return data
        return {}
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки users.json: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Пользователи сохранены: {len(users)} записей")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения users.json: {e}")

# ========== СТАТИСТИКА ==========
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"✅ Загружена статистика: {data.get('total_commands', 0)} команд")
                return data
        return {"total_commands": 0, "total_connections": 0, "users": {}}
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки stats.json: {e}")
        return {"total_commands": 0, "total_connections": 0, "users": {}}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Статистика сохранена")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения stats.json: {e}")

users_data = load_users()
stats_data = load_stats()
message_cache = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

def get_msk_time_short():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m %H:%M')

# ========== КЛАВИАТУРА ==========
def get_spam_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔥 Троллинг спам", callback_data="spam_troll")],
        [InlineKeyboardButton(text="⏳ В разработке", callback_data="spam_dev")],
        [InlineKeyboardButton(text="⏳ В разработке", callback_data="spam_dev2")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

INSULTS = [...]

# ========== ВСЕ КОМАНДЫ БОТА (ТЕ ЖЕ, ЧТО БЫЛИ РАНЬШЕ) ==========
# ... (get_ip_info, get_phone_info, delete_business_message, send_to_chat, handle_business_connection, handle_business_message и т.д.)

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info(f"📌 Загружено пользователей: {len(users_data)}")
    logger.info(f"📌 Всего команд: {stats_data.get('total_commands', 0)}")
    logger.info(f"📌 Время: {get_msk_time()} (МСК)")
    logger.info("=" * 60)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        if "Conflict" in str(e):
            logger.error("❌ КОНФЛИКТ: Бот уже запущен!")
            logger.info("⏹️ Останавливаем...")
            sys.exit(0)
        else:
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)
