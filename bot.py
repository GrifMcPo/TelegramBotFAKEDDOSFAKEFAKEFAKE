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

# ========== БЕЗОПАСНОЕ УДАЛЕНИЕ ==========
async def safe_delete(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"🗑️ Сообщение удалено из чата {chat_id}")
        return True
    except Exception as e:
        logger.debug(f"⚠️ Не удалось удалить: {e}")
        return False

# ========== ОБРАБОТЧИК ПОДКЛЮЧЕНИЯ ==========
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    logger.info("=" * 60)
    logger.info("🔗 ПОДКЛЮЧЕНИЕ К БИЗНЕС-АККАУНТУ!")
    logger.info(f"📌 ID подключения: {connection.id}")
    logger.info(f"📌 Пользователь: @{connection.user.username if connection.user else 'Нет'}")
    logger.info(f"📌 Может отвечать: {connection.can_reply}")
    logger.info("=" * 60)

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@dp.business_message()
async def handle_business_message(message: types.Message):
    try:
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ ИЗ ЛИЧНОГО ЧАТА")
        logger.info(f"📌 ОТ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info(f"📌 ID ЧАТА (куда отвечать): {message.chat.id}")
        logger.info("=" * 60)

        if not message.text:
            return

        text = message.text
        chat_id = message.chat.id  # ЭТО ID ЧАТА С СОБЕСЕДНИКОМ!
        message_id = message.message_id

        # ============================================================
        # КОМАНДА .ping
        # ============================================================
        if text.lower() == '.ping':
            logger.info("🎯 .ping")
            
            # Удаляем твоё сообщение из чата
            await safe_delete(chat_id, message_id)
            
            # Отправляем ответ В ТОТ ЖЕ ЧАТ (chat_id)
            await bot.send_message(
                chat_id=chat_id,
                text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}"
            )
            
            logger.info(f"✅ Ответ отправлен в чат {chat_id}")
            return

        # ============================================================
        # КОМАНДА .whois
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info("🎯 .whois")
            
            ip = text.replace('.whois', '').strip()
            
            if not ip:
                await safe_delete(chat_id, message_id)
                await bot.send_message(chat_id, "❌ Введите IP\nПример: .whois 8.8.8.8")
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await safe_delete(chat_id, message_id)
                await bot.send_message(chat_id, f"❌ Некорректный IP: {ip}")
                return
            
            # Удаляем твоё сообщение
            await safe_delete(chat_id, message_id)
            
            # Отправляем "загрузку" В ТОТ ЖЕ ЧАТ
            loading = await bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Поиск информации об IP {ip}..."
            )
            
            # Получаем данные
            result = await get_ip_info(ip)
            
            # Редактируем СВОЁ сообщение
            await loading.edit_text(result['text'])
            
            logger.info(f"✅ IP {ip} проверен в чате {chat_id}")
            return

        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            logger.info("🎯 .help")
            await safe_delete(chat_id, message_id)
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                    ".whois IP - информация об IP\n"
                    ".help - помощь\n"
                    ".ping - проверка\n"
                    "/chatid - ID чата\n\n"
                    "🔥 Бот удаляет команды и отвечает в этот же чат!"
                )
            )
            return

        # ============================================================
        # КОМАНДА /chatid
        # ============================================================
        if text.lower() == '/chatid':
            logger.info("🎯 /chatid")
            await safe_delete(chat_id, message_id)
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
                    f"🆔 ID ЧАТА: {chat_id}\n"
                    f"📌 ТИП: {message.chat.type}\n"
                    f"👤 ТВОЙ ID: {message.from_user.id}\n"
                    f"👤 ЮЗЕР: @{message.from_user.username or 'Нет'}"
                )
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
        "🤖 БОТ ДЛЯ ЛИЧНЫХ ЧАТОВ\n\n"
        "📌 КОМАНДЫ РАБОТАЮТ В ЧАТЕ С СОБЕСЕДНИКОМ:\n"
        ".whois IP - информация об IP\n"
        ".help - помощь\n"
        ".ping - проверка\n"
        "/chatid - ID чата\n\n"
        "🔥 Бот удаляет команды и отвечает в тот же чат!"
    )

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info("📌 Бот отвечает В ТОТ ЖЕ ЧАТ, где была команда")
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
