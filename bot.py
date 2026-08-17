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

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
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
logger.info("🚀 ЗАПУСК БОТА (УДАЛЕНИЕ + ОТВЕТ)")
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
                logger.debug(f"✅ Данные получены для IP: {ip}")
                return {'success': True, 'text': info_text, 'data': data}
            else:
                return {'success': False, 'text': f"❌ Не удалось получить данные: {data.get('message', 'Ошибка')}"}
        else:
            return {'success': False, 'text': f"❌ Ошибка API: {response.status_code}"}
    except Exception as e:
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

# ========== БЕЗОПАСНОЕ УДАЛЕНИЕ СООБЩЕНИЯ ==========
async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"✅ Сообщение {message_id} удалено из чата {chat_id}")
        return True
    except TelegramBadRequest as e:
        if "message to delete not found" in str(e):
            logger.warning(f"⚠️ Сообщение {message_id} уже удалено или не найдено")
        else:
            logger.error(f"❌ Ошибка удаления: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка удаления: {e}")
        return False

# ========== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_messages(message: types.Message):
    try:
        # ============================================================
        # ЛОГИРОВАНИЕ
        # ============================================================
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ")
        logger.info(f"📌 ТИП ЧАТА: {message.chat.type}")
        logger.info(f"📌 ID ЧАТА: {message.chat.id}")
        logger.info(f"📌 ID ПОЛЬЗОВАТЕЛЯ: {message.from_user.id}")
        logger.info(f"📌 ЮЗЕРНЕЙМ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info(f"📌 ID СООБЩЕНИЯ: {message.message_id}")
        logger.info("=" * 60)
        
        # ============================================================
        # РАБОТАЕМ ТОЛЬКО В ЛИЧНЫХ ЧАТАХ
        # ============================================================
        if message.chat.type != ChatType.PRIVATE:
            logger.info(f"⏭️ ИГНОРИРУЕМ: чат типа {message.chat.type}")
            return
        
        if not message.text:
            logger.info("⏭️ ИГНОРИРУЕМ: без текста")
            return
        
        text = message.text
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        chat_id = message.chat.id
        message_id = message.message_id
        
        # ============================================================
        # КОМАНДА .whois - УДАЛЯЕТ СООБЩЕНИЕ И ОТВЕЧАЕТ
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info(f"🎯 КОМАНДА .whois от @{username}")
            
            ip = text.replace('.whois', '').strip()
            logger.info(f"📌 IP: '{ip}'")
            
            if not ip:
                # Удаляем сообщение с командой
                await safe_delete_message(chat_id, message_id)
                # Отправляем ответ
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ ОШИБКА\n\nВведите IP-адрес\n📌 Пример: .whois 8.8.8.8"
                )
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                # Удаляем сообщение с командой
                await safe_delete_message(chat_id, message_id)
                # Отправляем ответ
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ НЕКОРРЕКТНЫЙ IP\n\nВведено: {ip}\n📌 Пример: 8.8.8.8"
                )
                return
            
            # ============================================================
            # УДАЛЯЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ С КОМАНДОЙ
            # ============================================================
            await safe_delete_message(chat_id, message_id)
            logger.info(f"🗑️ Сообщение с командой удалено")
            
            # ============================================================
            # ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ С "ЗАГРУЗКОЙ"
            # ============================================================
            loading_msg = await bot.send_message(
                chat_id=chat_id,
                text=f"🔍 ПОИСК ИНФОРМАЦИИ ОБ IP {ip}..."
            )
            logger.info(f"📤 Отправлено сообщение загрузки (ID: {loading_msg.message_id})")
            
            # Получаем данные
            result = await get_ip_info(ip)
            logger.info(f"📥 Получен результат от API: success={result['success']}")
            
            # ============================================================
            # РЕДАКТИРУЕМ СВОЕ СООБЩЕНИЕ (БОТ МОЖЕТ РЕДАКТИРОВАТЬ СВОИ)
            # ============================================================
            if result['success']:
                final_text = result['text']
                logger.info("📤 Отправка успешного результата")
            else:
                final_text = f"❌ ОШИБКА\n\n{result['text']}"
                logger.warning("📤 Отправка сообщения об ошибке")
            
            await loading_msg.edit_text(final_text)
            logger.info(f"✅ Сообщение отредактировано финальным результатом")
            logger.info(f"📌 ИТОГ: IP {ip} проверен для @{username} в чате {chat_id}")
            return
        
        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            logger.info(f"📖 ПОКАЗ HELP для @{username}")
            # Удаляем сообщение с командой
            await safe_delete_message(chat_id, message_id)
            # Отправляем ответ
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                    ".whois IP - информация об IP (удаляет команду)\n"
                    ".help - помощь (удаляет команду)\n"
                    ".ping - проверка (удаляет команду)\n"
                    "/chatid - ID чата (удаляет команду)\n\n"
                    "🔥 Бот удаляет твои команды и отвечает чисто!"
                )
            )
            return
        
        # ============================================================
        # КОМАНДА .ping
        # ============================================================
        if text.lower() == '.ping':
            logger.info(f"🏓 PING от @{username}")
            await safe_delete_message(chat_id, message_id)
            await bot.send_message(
                chat_id=chat_id,
                text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}"
            )
            return
        
        # ============================================================
        # КОМАНДА /chatid
        # ============================================================
        if text.lower() == '/chatid':
            logger.info(f"🎯 КОМАНДА /chatid от @{username}")
            
            # Удаляем сообщение с командой
            await safe_delete_message(chat_id, message_id)
            
            chat_info = (
                f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
                f"🆔 ID ЧАТА: {chat_id}\n"
                f"📌 ТИП: {message.chat.type}\n"
                f"👤 ТВОЙ ID: {user_id}\n"
                f"👤 ЮЗЕРНЕЙМ: @{username}\n"
                f"🕐 ВРЕМЯ: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            )
            
            try:
                # Отправляем в ЛС пользователя
                await bot.send_message(chat_id=user_id, text=chat_info)
                # Отправляем в чат подтверждение
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ ID чата отправлен тебе в ЛС\n🆔 {chat_id}"
                )
                logger.info(f"✅ ID чата {chat_id} отправлен в ЛС пользователю @{username}")
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке в ЛС: {e}")
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ НЕ УДАЛОСЬ ОТПРАВИТЬ В ЛС\n\n🆔 ID ЧАТА: {chat_id}"
                )
            
            return
        
        # ============================================================
        # КОМАНДА НЕ РАСПОЗНАНА
        # ============================================================
        logger.info(f"⏭️ Команда не распознана: '{text}'")
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В HANDLE_MESSAGES: {e}")
        logger.error(traceback.format_exc())
        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"❌ Ошибка: {str(e)}"
            )
        except:
            pass

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        logger.info(f"👤 Пользователь @{username} (ID: {user_id}) запустил бота")
        
        await message.answer(
            "🤖 БОТ АКТИВЕН\n\n"
            "📌 КОМАНДЫ:\n\n"
            ".whois IP - информация об IP (удаляет команду)\n"
            ".help - помощь (удаляет команду)\n"
            ".ping - проверка (удаляет команду)\n"
            "/chatid - ID чата (удаляет команду)\n\n"
            "💡 Пример: .whois 8.8.8.8\n\n"
            "🔥 Бот удаляет твои команды и отвечает чисто!"
        )
        logger.info(f"✅ Ответ на /start отправлен пользователю @{username}")
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")

# ========== КОМАНДА /STATUS ==========
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
            f"📌 Режим: Удаление + Ответ\n"
            f"📌 Команды: .whois, .help, .ping, /chatid"
        )
        await message.reply(stats)
        logger.info(f"✅ Статистика отправлена админу")
    except Exception as e:
        logger.error(f"❌ Ошибка в /status: {e}")

# ========== ЗАПУСК ==========
async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔥 БОТ ЗАПУЩЕН!")
        logger.info("🤖 Бот УДАЛЯЕТ команды и ОТВЕЧАЕТ в чат")
        logger.info("📌 .whois IP - удаляет команду, показывает IP")
        logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
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
