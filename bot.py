import asyncio
import os
import sys
import logging
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BusinessConnection, BusinessMessagesDeleted

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

# Храним ID подключения
connection_id = None

# ========== ФУНКЦИЯ ДЛЯ ПРОБИВА IP ==========
async def get_ip_info(ip: str):
    try:
        response = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                info_text = (
                    f"✅ ИНФОРМАЦИЯ ОБ IP\n\n"
                    f"🌐 IP: {data['query']}\n"
                    f"🌍 Страна: {data['country']} {data.get('countryCode', '')}\n"
                    f"🏙️ Регион: {data['regionName']}\n"
                    f"🏙️ Город: {data['city']}\n"
                    f"📍 Координаты: {data['lat']}, {data['lon']}\n"
                    f"🗺️ Карта: https://maps.google.com/maps?q={data['lat']},{data['lon']}\n"
                    f"📡 Провайдер: {data['isp']}\n"
                    f"🏢 Организация: {data['org']}\n"
                    f"🔗 AS: {data['as']} ({data.get('asname', '')})\n"
                    f"⏰ Часовой пояс: {data['timezone']}"
                )
                return {'success': True, 'text': info_text}
            else:
                return {'success': False, 'text': f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}"}
        else:
            return {'success': False, 'text': f"❌ Ошибка API: {response.status_code}"}
    except Exception as e:
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

# ========== ОБРАБОТЧИК ПОДКЛЮЧЕНИЯ К БИЗНЕС-АККАУНТУ ==========
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    global connection_id
    connection_id = connection.id
    logger.info(f"🔗 ПОДКЛЮЧЕНИЕ К БИЗНЕС-АККАУНТУ!")
    logger.info(f"📌 ID подключения: {connection_id}")
    logger.info(f"📌 Пользователь: @{connection.user.username or 'Нет'}")
    logger.info(f"📌 Может отвечать: {connection.can_reply}")

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ИЗ ЛИЧНЫХ ЧАТОВ ==========
@dp.business_message()
async def handle_business_message(message: types.Message):
    try:
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ ИЗ ЛИЧНОГО ЧАТА (BUSINESS API)")
        logger.info(f"📌 ID ПОДКЛЮЧЕНИЯ: {message.business_connection_id}")
        logger.info(f"📌 ОТ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info("=" * 60)

        if not message.text:
            return

        text = message.text
        chat_id = message.chat.id

        # .whois
        if text.lower().startswith('.whois'):
            ip = text.replace('.whois', '').strip()
            
            if not ip:
                await message.answer("❌ Введите IP\nПример: .whois 8.8.8.8")
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await message.answer(f"❌ Некорректный IP: {ip}")
                return
            
            loading = await message.answer(f"🔍 Поиск информации об IP {ip}...")
            result = await get_ip_info(ip)
            await loading.edit_text(result['text'])
            return

        # .help
        if text.lower() == '.help':
            await message.answer(
                "🤖 КОМАНДЫ\n\n"
                ".whois IP - информация об IP\n"
                ".help - помощь\n"
                ".ping - проверка"
            )
            return

        # .ping
        if text.lower() == '.ping':
            await message.answer(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")
            return

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🤖 БОТ ДЛЯ ЛИЧНЫХ ЧАТОВ (BUSINESS API)\n\n"
        "📌 ЧТОБЫ ПОДКЛЮЧИТЬ БОТА:\n"
        "1. @BotFather → /mybots → выбери бота → Bot Settings → Business Mode → Turn on\n"
        "2. Настройки Telegram → Telegram Business → Чат-боты → Добавить @gredyr_bot\n"
        "3. Выбери чаты, где бот должен работать\n\n"
        "📌 КОМАНДЫ:\n"
        ".whois IP - информация об IP\n"
        ".help - помощь\n"
        ".ping - проверка"
    )

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ДЛЯ ЛИЧНЫХ ЧАТОВ (BUSINESS API)")
    logger.info("📌 Бот будет получать сообщения из ЛИЧНЫХ чатов")
    logger.info("📌 Для подключения используй /start")
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
