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
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(
    level=logging.DEBUG,
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

logger.info("=" * 60)
logger.info("🚀 ЗАПУСК БОТА")
logger.info(f"🤖 Токен: {BOT_TOKEN[:15]}...")
logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
logger.info("=" * 60)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_ip_info(ip: str):
    try:
        logger.debug(f"📡 Запрос к API для IP: {ip}")
        response = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query',
            timeout=10
        )
        logger.debug(f"📡 Ответ API: статус {response.status_code}")
        
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

async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"✅ Сообщение {message_id} удалено")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить: {e}")
        return False

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@dp.message()
async def handle_messages(message: types.Message):
    try:
        # ============================================================
        # МАКСИМАЛЬНОЕ ЛОГИРОВАНИЕ
        # ============================================================
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ")
        logger.info(f"📌 ТИП ЧАТА: {message.chat.type}")
        logger.info(f"📌 ID ЧАТА: {message.chat.id}")
        logger.info(f"📌 ID ПОЛЬЗОВАТЕЛЯ: {message.from_user.id}")
        logger.info(f"📌 ЮЗЕРНЕЙМ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ТЕКСТ: '{message.text}'")
        logger.info(f"📌 ID СООБЩЕНИЯ: {message.message_id}")
        logger.info("=" * 60)
        
        # ============================================================
        # ПРОВЕРКА: РАБОТАЕМ В ЛЮБЫХ ЧАТАХ (ДЛЯ ТЕСТА)
        # ============================================================
        # УБИРАЕМ ПРОВЕРКУ НА PRIVATE, ЧТОБЫ ВИДЕТЬ ВСЕ СООБЩЕНИЯ
        logger.info(f"📌 РАБОТАЕМ В ЧАТЕ ТИПА: {message.chat.type}")
        
        if not message.text:
            logger.info("⏭️ БЕЗ ТЕКСТА")
            return
        
        text = message.text
        chat_id = message.chat.id
        message_id = message.message_id
        username = message.from_user.username or "Нет юзернейма"
        
        # ============================================================
        # ТЕСТОВЫЙ ОТВЕТ НА ЛЮБОЕ СООБЩЕНИЕ
        # ============================================================
        # Раскомментируй для теста:
        # await message.reply(f"✅ Бот видит сообщение: {text[:50]}...")
        # return
        
        # ============================================================
        # КОМАНДА .whois
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info(f"🎯 НАЙДЕНА КОМАНДА .whois")
            
            ip = text.replace('.whois', '').strip()
            logger.info(f"📌 IP: '{ip}'")
            
            if not ip:
                await safe_delete_message(chat_id, message_id)
                await bot.send_message(chat_id, "❌ Введите IP\nПример: .whois 8.8.8.8")
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await safe_delete_message(chat_id, message_id)
                await bot.send_message(chat_id, f"❌ Некорректный IP: {ip}")
                return
            
            # Удаляем команду
            await safe_delete_message(chat_id, message_id)
            
            # Отправляем загрузку
            loading = await bot.send_message(chat_id, f"🔍 Поиск информации об IP {ip}...")
            
            # Получаем данные
            result = await get_ip_info(ip)
            
            # Редактируем
            await loading.edit_text(result['text'])
            
            logger.info(f"✅ IP {ip} проверен")
            return
        
        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            await safe_delete_message(chat_id, message_id)
            await bot.send_message(
                chat_id,
                "🤖 КОМАНДЫ\n\n"
                ".whois IP - информация об IP\n"
                ".help - помощь\n"
                ".ping - проверка\n"
                "/chatid - ID чата"
            )
            return
        
        # ============================================================
        # КОМАНДА .ping
        # ============================================================
        if text.lower() == '.ping':
            await safe_delete_message(chat_id, message_id)
            await bot.send_message(chat_id, f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")
            return
        
        # ============================================================
        # КОМАНДА /chatid
        # ============================================================
        if text.lower() == '/chatid':
            await safe_delete_message(chat_id, message_id)
            await bot.send_message(
                chat_id,
                f"🆔 ID ЧАТА: {chat_id}\n📌 ТИП: {message.chat.type}"
            )
            return
        
        logger.info(f"⏭️ НЕ РАСПОЗНАНА: '{text}'")
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        logger.error(traceback.format_exc())

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        logger.info(f"👤 /start от @{message.from_user.username}")
        await message.answer(
            "🤖 БОТ АКТИВЕН\n\n"
            ".whois IP - информация об IP\n"
            ".help - помощь\n"
            ".ping - проверка\n"
            "/chatid - ID чата\n\n"
            "💡 Пример: .whois 8.8.8.8"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка /start: {e}")

# ========== ЗАПУСК ==========
async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔥 БОТ ЗАПУЩЕН!")
        logger.info("🤖 Бот слушает ВСЕ сообщения во ВСЕХ чатах")
        logger.info("📌 Для проверки напиши ЛЮБОЕ сообщение")
        logger.info("=" * 60)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)
