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
        logger.info(f"📌 ID СООБЩЕНИЯ: {message.message_id}")
        logger.info("=" * 60)

        if not message.text:
            return

        text = message.text
        chat_id = message.chat.id
        message_id = message.message_id

        # ============================================================
        # КОМАНДА .ping - РЕДАКТИРУЕТ ТВОЁ СООБЩЕНИЕ
        # ============================================================
        if text.lower() == '.ping':
            logger.info("🎯 .ping - РЕДАКТИРУЮ ТВОЁ СООБЩЕНИЕ")
            
            try:
                # РЕДАКТИРУЕМ ТВОЁ СООБЩЕНИЕ!
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}"
                )
                logger.info("✅ Твоё сообщение отредактировано на Pong")
            except Exception as e:
                logger.error(f"❌ Ошибка редактирования: {e}")
                # Если не получилось отредактировать — отвечаем
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}"
                )
            
            return

        # ============================================================
        # КОМАНДА .whois - РЕДАКТИРУЕТ ТВОЁ СООБЩЕНИЕ
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info("🎯 .whois - РЕДАКТИРУЮ ТВОЁ СООБЩЕНИЕ")
            
            ip = text.replace('.whois', '').strip()
            
            if not ip:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="❌ ОШИБКА\n\nВведите IP-адрес\n📌 Пример: .whois 8.8.8.8"
                    )
                except:
                    await bot.send_message(chat_id, "❌ Введите IP\nПример: .whois 8.8.8.8")
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"❌ НЕКОРРЕКТНЫЙ IP\n\nВведено: {ip}\n📌 Пример: 8.8.8.8"
                    )
                except:
                    await bot.send_message(chat_id, f"❌ Некорректный IP: {ip}")
                return
            
            try:
                # 1. РЕДАКТИРУЕМ ТВОЁ СООБЩЕНИЕ НА "ЗАГРУЗКУ"
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🔍 ПОИСК ИНФОРМАЦИИ ОБ IP {ip}..."
                )
                
                # 2. ПОЛУЧАЕМ ДАННЫЕ
                result = await get_ip_info(ip)
                
                # 3. СНОВА РЕДАКТИРУЕМ ТВОЁ СООБЩЕНИЕ (ФИНАЛ)
                if result['success']:
                    final_text = result['text']
                else:
                    final_text = f"❌ ОШИБКА\n\n{result['text']}"
                
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=final_text
                )
                
                logger.info(f"✅ Твоё сообщение отредактировано на инфу об IP {ip}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка редактирования: {e}")
                # Если не получилось — отвечаем новым сообщением
                result = await get_ip_info(ip)
                await bot.send_message(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}")
            
            return

        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            logger.info("🎯 .help")
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=(
                        "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                        ".whois IP - информация об IP\n"
                        ".help - помощь\n"
                        ".ping - проверка\n"
                        "/chatid - ID чата\n\n"
                        "🔥 Бот РЕДАКТИРУЕТ твои сообщения!"
                    )
                )
            except:
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                        ".whois IP - информация об IP\n"
                        ".help - помощь\n"
                        ".ping - проверка\n"
                        "/chatid - ID чата"
                    )
                )
            return

        # ============================================================
        # КОМАНДА /chatid
        # ============================================================
        if text.lower() == '/chatid':
            logger.info("🎯 /chatid")
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=(
                        f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
                        f"🆔 ID ЧАТА: {chat_id}\n"
                        f"📌 ТИП: {message.chat.type}\n"
                        f"👤 ТВОЙ ID: {message.from_user.id}\n"
                        f"👤 ЮЗЕР: @{message.from_user.username or 'Нет'}"
                    )
                )
            except:
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
        "🤖 БОТ ДЛЯ БИЗНЕС-ЧАТОВ\n\n"
        "📌 КОМАНДЫ РЕДАКТИРУЮТ ТВОИ СООБЩЕНИЯ:\n\n"
        ".whois IP - информация об IP\n"
        ".help - помощь\n"
        ".ping - проверка\n"
        "/chatid - ID чата\n\n"
        "🔥 Пример: .whois 8.8.8.8\n"
        "Твоё сообщение ЗАМЕНИТСЯ на информацию об IP!"
    )

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info("📌 Бот РЕДАКТИРУЕТ твои сообщения в бизнес-чате")
    logger.info("📌 Ты пишешь .ping → сообщение становится Pong!")
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
