import asyncio
import os
import sys
import logging
import re
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types.business_connection import BusinessConnection

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

# ========== ФУНКЦИЯ ДЛЯ ПРОБИВА НОМЕРА ==========
async def get_phone_info(phone: str):
    try:
        phone_clean = phone.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        if not phone_clean.isdigit():
            return {'success': False, 'text': "❌ Некорректный номер\n📌 Пример: 89001234567"}
        
        try:
            parsed = phonenumbers.parse(phone_clean, None)
            if not phonenumbers.is_valid_number(parsed):
                return {'success': False, 'text': "❌ Номер не существует"}
        except:
            try:
                parsed = phonenumbers.parse(phone_clean, "RU")
                if not phonenumbers.is_valid_number(parsed):
                    return {'success': False, 'text': "❌ Номер не существует"}
            except:
                return {'success': False, 'text': "❌ Некорректный номер"}
        
        operator = carrier.name_for_number(parsed, "ru") or "Не определен"
        region = geocoder.description_for_number(parsed, "ru") or "Не определен"
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        
        info_text = (
            f"✅ ИНФОРМАЦИЯ О НОМЕРЕ\n\n"
            f"📱 Номер: {formatted}\n"
            f"📡 Оператор: {operator}\n"
            f"🌍 Регион: {region}\n"
            f"🏙️ Город регистрации: {region.split()[0] if region else 'Не определен'}"
        )
        return {'success': True, 'text': info_text}
        
    except Exception as e:
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

# ========== ОТПРАВКА В БИЗНЕС-ЧАТ ==========
async def send_business_message(chat_id: int, text: str, connection_id: str = None):
    try:
        if connection_id:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                business_connection_id=connection_id
            )
        else:
            return await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")
        return None

# ========== ОБРАБОТЧИК ПОДКЛЮЧЕНИЯ ==========
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    logger.info("=" * 60)
    logger.info("🔗 ПОДКЛЮЧЕНИЕ К БИЗНЕС-АККАУНТУ!")
    logger.info(f"📌 ID подключения: {connection.id}")
    logger.info(f"📌 Пользователь: @{connection.user.username if connection.user else 'Нет'}")
    logger.info("=" * 60)

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@dp.business_message()
async def handle_business_message(message: types.Message):
    try:
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ ИЗ БИЗНЕС-ЧАТА")
        logger.info(f"📌 ОТ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info("=" * 60)

        if not message.text:
            return

        text = message.text
        chat_id = message.chat.id
        connection_id = message.business_connection_id

        # ============================================================
        # КОМАНДА .inf - СПРАВКА
        # ============================================================
        if text.lower() == '.inf':
            logger.info("🎯 .inf")
            
            await send_business_message(
                chat_id=chat_id,
                text=(
                    "📚 СПРАВКА ПО КОМАНДАМ\n\n"
                    "👤 Твоя подписка: LEADER\n\n"
                    "📌 Формат: .команда - описание\n\n"
                    "🐢 ПРОБИВ\n"
                    "────────────────────\n"
                    ".whois ip [IP] - Пробив по IP-адресу\n"
                    ".whois number [НОМЕР] - Пробив по номеру телефона\n\n"
                    "⚡ ДРУГОЕ\n"
                    "────────────────────\n"
                    ".ping - Проверка работы бота\n"
                    ".inf - Эта справка"
                ),
                connection_id=connection_id
            )
            return

        # ============================================================
        # КОМАНДА .whois ip - ПРОБИВ ПО IP
        # ============================================================
        if text.lower().startswith('.whois ip'):
            logger.info("🎯 .whois ip")
            
            ip = text.replace('.whois ip', '').strip()
            
            if not ip:
                await send_business_message(chat_id, "❌ Введите IP-адрес\n📌 Пример: .whois ip 8.8.8.8", connection_id)
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await send_business_message(chat_id, f"❌ Некорректный IP: {ip}\n📌 Пример: 8.8.8.8", connection_id)
                return
            
            result = await get_ip_info(ip)
            await send_business_message(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}", connection_id)
            
            logger.info(f"✅ IP {ip} проверен")
            return

        # ============================================================
        # КОМАНДА .whois number - ПРОБИВ ПО НОМЕРУ
        # ============================================================
        if text.lower().startswith('.whois number'):
            logger.info("🎯 .whois number")
            
            phone = text.replace('.whois number', '').strip()
            
            if not phone:
                await send_business_message(chat_id, "❌ Введите номер телефона\n📌 Пример: .whois number 89001234567", connection_id)
                return
            
            result = await get_phone_info(phone)
            await send_business_message(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}", connection_id)
            
            logger.info(f"✅ Номер {phone} проверен")
            return

        # ============================================================
        # КОМАНДА .ping
        # ============================================================
        if text.lower() == '.ping':
            logger.info("🎯 .ping")
            
            await send_business_message(
                chat_id=chat_id,
                text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}",
                connection_id=connection_id
            )
            
            logger.info("✅ Ответ отправлен")
            return

        # ============================================================
        # КОМАНДА /chatid
        # ============================================================
        if text.lower() == '/chatid':
            logger.info("🎯 /chatid")
            await send_business_message(
                chat_id=chat_id,
                text=(
                    f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
                    f"🆔 ID ЧАТА: {chat_id}\n"
                    f"📌 ТИП: {message.chat.type}\n"
                    f"👤 ТВОЙ ID: {message.from_user.id}\n"
                    f"👤 ЮЗЕР: @{message.from_user.username or 'Нет'}"
                ),
                connection_id=connection_id
            )
            return

        logger.info(f"⏭️ НЕ РАСПОЗНАНА: {text}")

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🤖 БОТ ДЛЯ БИЗНЕС-ЧАТОВ\n\n"
        "📌 Введи .inf для справки\n\n"
        "📌 КОМАНДЫ:\n"
        ".whois ip [IP] - пробив по IP\n"
        ".whois number [НОМЕР] - пробив по номеру\n"
        ".ping - проверка\n"
        ".inf - справка"
    )

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info("📌 Команды: .inf, .whois ip, .whois number, .ping")
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
