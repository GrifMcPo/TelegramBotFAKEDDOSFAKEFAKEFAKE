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
from aiogram.types import ChatType

# ========== НАСТРОЙКА МОЩНОГО ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.DEBUG,  # Меняем на DEBUG для максимальной детализации
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
logger.info("🚀 ЗАПУСК БОТА ДЛЯ ЛИЧНЫХ ЧАТОВ")
logger.info(f"🤖 Токен: {BOT_TOKEN[:15]}...")
logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
logger.info("=" * 60)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ФУНКЦИЯ ДЛЯ ПРОБИВА IP ==========
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
                logger.debug(f"✅ Данные получены для IP: {ip}")
                return {'success': True, 'text': info_text, 'data': data}
            else:
                logger.warning(f"⚠️ API вернул ошибку для {ip}: {data.get('message', 'Unknown')}")
                return {'success': False, 'text': f"❌ Не удалось получить данные: {data.get('message', 'Ошибка')}"}
        else:
            logger.error(f"❌ Ошибка API: {response.status_code} для {ip}")
            return {'success': False, 'text': f"❌ Ошибка API: {response.status_code}"}
    except requests.exceptions.Timeout:
        logger.error(f"❌ Таймаут API для {ip}")
        return {'success': False, 'text': "❌ Превышено время ожидания ответа от сервера"}
    except Exception as e:
        logger.error(f"❌ Ошибка при запросе к API: {e}")
        logger.error(traceback.format_exc())
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

# ========== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_messages(message: types.Message):
    try:
        # ============================================================
        # МОЩНОЕ ЛОГИРОВАНИЕ ВСЕХ ВХОДЯЩИХ СООБЩЕНИЙ
        # ============================================================
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ")
        logger.info(f"📌 ТИП ЧАТА: {message.chat.type}")
        logger.info(f"📌 ID ЧАТА: {message.chat.id}")
        logger.info(f"📌 ID ПОЛЬЗОВАТЕЛЯ: {message.from_user.id}")
        logger.info(f"📌 ЮЗЕРНЕЙМ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ИМЯ: {message.from_user.full_name}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info(f"📌 ЕСТЬ ЛИ ТЕКСТ: {bool(message.text)}")
        logger.info("=" * 60)
        
        # ============================================================
        # ПРОВЕРКА: РАБОТАЕМ ТОЛЬКО В ЛИЧНЫХ ЧАТАХ
        # ============================================================
        if message.chat.type != ChatType.PRIVATE:
            logger.info(f"⏭️ ИГНОРИРУЕМ: чат типа {message.chat.type} (не PRIVATE)")
            return
        else:
            logger.info("✅ РАБОТАЕМ: чат типа PRIVATE (личный чат)")
        
        if not message.text:
            logger.info("⏭️ ИГНОРИРУЕМ: сообщение без текста")
            return
        
        text = message.text
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        chat_id = message.chat.id
        
        # ============================================================
        # ОБРАБОТКА КОМАНДЫ .whois
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info(f"🎯 ОБНАРУЖЕНА КОМАНДА .whois от @{username}")
            
            ip = text.replace('.whois', '').strip()
            logger.info(f"📌 IP после очистки: '{ip}'")
            
            if not ip:
                logger.warning("⚠️ IP не указан")
                await message.reply(
                    "❌ Введите IP-адрес\n\n"
                    "📌 Пример: .whois 8.8.8.8"
                )
                return
            
            # Валидация IP
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                logger.warning(f"⚠️ Некорректный IP: {ip}")
                await message.reply(
                    "❌ Некорректный IP-адрес\n\n"
                    "📌 Пример правильного IP: 8.8.8.8"
                )
                return
            
            logger.info(f"✅ IP валидный: {ip}")
            logger.info(f"📤 ОТПРАВКА ЗАПРОСА К API...")
            
            # Отправляем "загрузку"
            loading_msg = await message.reply("🔍 Поиск информации об IP...")
            logger.info(f"📤 Отправлено сообщение загрузки (ID: {loading_msg.message_id})")
            
            # Получаем данные
            result = await get_ip_info(ip)
            logger.info(f"📥 Получен результат от API: success={result['success']}")
            
            # Редактируем сообщение с результатом
            if result['success']:
                final_text = f"✅ ИНФОРМАЦИЯ ОБ IP\n\n{result['text']}"
                logger.info(f"📤 Отправка успешного результата")
            else:
                final_text = result['text']
                logger.warning(f"📤 Отправка сообщения об ошибке")
            
            await loading_msg.edit_text(final_text)
            logger.info(f"✅ Сообщение отредактировано")
            logger.info(f"📌 ИТОГ: IP {ip} проверен для @{username} в чате {chat_id}")
            return
        
        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            logger.info(f"📖 ПОКАЗ HELP для @{username}")
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
        
        # ============================================================
        # КОМАНДА .ping
        # ============================================================
        if text.lower() == '.ping':
            logger.info(f"🏓 PING от @{username}")
            await message.reply(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")
            return
        
        # ============================================================
        # КОМАНДА НЕ РАСПОЗНАНА
        # ============================================================
        logger.info(f"⏭️ Команда не распознана: '{text}'")
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В HANDLE_MESSAGES: {e}")
        logger.error(traceback.format_exc())

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        logger.info(f"👤 Пользователь @{username} (ID: {user_id}) запустил бота (команда /start)")
        
        await message.answer(
            "🤖 БОТ АКТИВЕН\n\n"
            "📌 Бот работает ТОЛЬКО в личных чатах\n\n"
            "📌 Используйте команды:\n\n"
            ".whois IP - информация об IP\n"
            ".help - список команд\n"
            ".ping - проверка бота\n\n"
            "💡 Пример: .whois 8.8.8.8"
        )
        logger.info(f"✅ Ответ на /start отправлен пользователю @{username}")
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")
        logger.error(traceback.format_exc())

# ========== КОМАНДА /STATUS (ДЛЯ АДМИНА) ==========
@dp.message(Command("status"))
async def status_command(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        if user_id != ADMIN_ID:
            logger.warning(f"⚠️ Пользователь @{username} пытался вызвать /status (не админ)")
            await message.reply("❌ Нет прав")
            return
        
        logger.info(f"📊 Админ @{username} запросил статистику")
        
        bot_info = await bot.get_me()
        stats = (
            f"📊 СТАТИСТИКА БОТА\n\n"
            f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"👤 Админ: {ADMIN_ID}\n"
            f"🤖 Бот: @{bot_info.username}\n"
            f"🆔 ID бота: {bot_info.id}\n"
            f"📌 Режим: Только личные чаты\n"
            f"📌 Доступные команды: .whois, .help, .ping"
        )
        await message.reply(stats)
        logger.info(f"✅ Статистика отправлена админу")
    except Exception as e:
        logger.error(f"❌ Ошибка в /status: {e}")
        logger.error(traceback.format_exc())

# ========== ЗАПУСК ==========
async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔥 БОТ ДЛЯ ЛИЧНЫХ ЧАТОВ ЗАПУЩЕН!")
        logger.info("🤖 Бот работает ТОЛЬКО в личных чатах (PRIVATE)")
        logger.info("📌 ИГНОРИРУЕТ: группы, каналы, супергруппы")
        logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
        logger.info("📌 ДОСТУПНЫЕ КОМАНДЫ:")
        logger.info("   .whois IP - информация об IP")
        logger.info("   .help - помощь")
        logger.info("   .ping - проверка")
        logger.info("=" * 60)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
