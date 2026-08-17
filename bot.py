import asyncio
import os
import sys
import logging
import traceback
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
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
                return {'success': True, 'text': info_text, 'data': data}
            else:
                return {'success': False, 'text': f"❌ Не удалось получить данные: {data.get('message', 'Ошибка')}"}
        else:
            return {'success': False, 'text': f"❌ Ошибка API: {response.status_code}"}
    except Exception as e:
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

# ========== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_messages(message: types.Message):
    try:
        if not message.text:
            return
        
        text = message.text
        chat_id = message.chat.id
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        # ========== КОМАНДА .whois ==========
        if text.lower().startswith('.whois'):
            ip = text.replace('.whois', '').strip()
            
            # Проверка что IP введен
            if not ip:
                await message.reply(
                    "❌ Введите IP-адрес\n\n"
                    "📌 Пример: .whois 8.8.8.8"
                )
                return
            
            # Валидация IP (простая проверка)
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await message.reply(
                    "❌ Некорректный IP-адрес\n\n"
                    "📌 Пример правильного IP: 8.8.8.8"
                )
                return
            
            logger.info(f"📌 Пользователь @{username} (ID: {user_id}) запросил IP: {ip} в чате {chat_id}")
            
            # Отправляем "загрузку"
            loading_msg = await message.reply("🔍 Поиск информации об IP...")
            
            # Получаем данные
            result = await get_ip_info(ip)
            
            # Редактируем сообщение с результатом
            if result['success']:
                await loading_msg.edit_text(
                    f"✅ ИНФОРМАЦИЯ ОБ IP\n\n"
                    f"{result['text']}"
                )
            else:
                await loading_msg.edit_text(result['text'])
            
            logger.info(f"✅ IP проверен: {ip} для пользователя @{username}")
            return
        
        # ========== КОМАНДА .help ==========
        if text.lower() == '.help':
            help_text = (
                "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                "📌 .whois IP\n"
                "   → Показывает информацию об IP-адресе\n"
                "   Пример: .whois 8.8.8.8\n\n"
                "📌 .help\n"
                "   → Показывает это сообщение\n\n"
                "📌 .ping\n"
                "   → Проверка работы бота"
            )
            await message.reply(help_text)
            return
        
        # ========== КОМАНДА .ping ==========
        if text.lower() == '.ping':
            await message.reply(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")
            return
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_messages: {e}")
        logger.error(traceback.format_exc())

# ========== КОМАНДА /START (для регистрации) ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        logger.info(f"👤 Пользователь @{username} (ID: {user_id}) запустил бота")
        
        await message.answer(
            "🤖 БОТ АКТИВЕН\n\n"
            "📌 Используйте команды в ЛЮБОМ чате:\n\n"
            ".whois IP - информация об IP\n"
            ".help - список команд\n"
            ".ping - проверка бота\n\n"
            "💡 Пример: .whois 8.8.8.8"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")

# ========== КОМАНДА /STATUS (для админа) ==========
@dp.message(Command("status"))
async def status_command(message: types.Message):
    try:
        if message.from_user.id != ADMIN_ID:
            await message.reply("❌ Нет прав")
            return
        
        bot_info = await bot.get_me()
        stats = (
            f"📊 СТАТИСТИКА БОТА\n\n"
            f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"👤 Админ: {ADMIN_ID}\n"
            f"🤖 Бот: @{bot_info.username}\n"
            f"🆔 ID бота: {bot_info.id}\n"
            f"📌 Режим: Business Bot\n"
            f"📌 Доступные команды: .whois, .help, .ping"
        )
        await message.reply(stats)
    except Exception as e:
        logger.error(f"❌ Ошибка в /status: {e}")

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 TELEGRAM BUSINESS БОТ ЗАПУЩЕН!")
    logger.info("🤖 Бот обрабатывает команды в ЛЮБЫХ чатах")
    logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
    logger.info("📌 ДОСТУПНЫЕ КОМАНДЫ:")
    logger.info("   .whois IP - информация об IP")
    logger.info("   .help - помощь")
    logger.info("   .ping - проверка")
    logger.info("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
