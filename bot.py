import asyncio
import os
import sys
import logging
import re
import requests
import random
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime
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
ADMIN_ID = int(os.getenv("ADMIN_ID", "8857252828"))

if not BOT_TOKEN:
    logger.error("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КЕШ СООБЩЕНИЙ ДЛЯ ВЕБХУКА ==========
message_cache = {}
INSULTS = [...]

# ========== ВСЕ ОСТАЛЬНЫЕ ФУНКЦИИ (get_ip_info, get_phone_info, delete_business_message, send_business_message) ==========

# ========== ОСНОВНОЙ ОБРАБОТЧИК С КЕШИРОВАНИЕМ ==========
@dp.business_message()
async def handle_business_message(message: types.Message):
    try:
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ ИЗ БИЗНЕС-ЧАТА")
        logger.info(f"📌 ОТ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info(f"📌 ID СООБЩЕНИЯ: {message.message_id}")
        logger.info("=" * 60)

        # ============================================================
        # СОХРАНЯЕМ В КЕШ ДЛЯ ВЕБХУКА
        # ============================================================
        chat_id = message.chat.id
        msg_id = message.message_id
        from_user = message.from_user.username or "Неизвестно"
        text = message.text or "[Медиафайл]"
        
        cache_key = f"{chat_id}_{msg_id}"
        message_cache[cache_key] = (text, from_user)
        
        # Ограничиваем кеш (максимум 1000 сообщений)
        if len(message_cache) > 1000:
            oldest = min(message_cache.keys())
            del message_cache[oldest]

        if not message.text:
            return

        text = message.text
        message_id = message.message_id
        connection_id = message.business_connection_id

        # ============================================================
        # ВСЕ КОМАНДЫ (такие же как в предыдущей версии)
        # ============================================================
        # .inf, .spam, .spams, .whois, .ping, /chatid

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info("📌 Бот кеширует сообщения для вебхука")
    logger.info("📌 Удаления отслеживаются через вебхук")
    logger.info("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)
