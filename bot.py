import asyncio
import os
import sys
import logging
import traceback
import re
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType

# ========== НАСТРОЙКА МОЩНОГО ЛОГИРОВАНИЯ ==========
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
logger.info("🚀 ЗАПУСК БОТА ДЛЯ ЛИЧНЫХ ЧАТОВ")
logger.info(f"🤖 Токен: {BOT_TOKEN[:15]}...")
logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
logger.info("=" * 60)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== ХРАНИЛИЩЕ ДЛЯ ОТСЛЕЖИВАНИЯ ==========
processed_messages = set()  # Чтобы не обрабатывать одно сообщение дважды

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
                return {'success': False, 'text': f"❌ Не удалось получить данные: {data.get('message', 'Ошибка')}"}
        else:
            return {'success': False, 'text': f"❌ Ошибка API: {response.status_code}"}
    except Exception as e:
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

# ========== ОСНОВНОЙ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_messages(message: types.Message):
    try:
        # ============================================================
        # МОЩНОЕ ЛОГИРОВАНИЕ КАЖДОГО СООБЩЕНИЯ
        # ============================================================
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ")
        logger.info(f"📌 ID СООБЩЕНИЯ: {message.message_id}")
        logger.info(f"📌 ТИП ЧАТА: {message.chat.type}")
        logger.info(f"📌 ID ЧАТА: {message.chat.id}")
        logger.info(f"📌 НАЗВАНИЕ ЧАТА: {message.chat.full_name if hasattr(message.chat, 'full_name') else 'Нет'}")
        logger.info(f"📌 ID ПОЛЬЗОВАТЕЛЯ: {message.from_user.id}")
        logger.info(f"📌 ЮЗЕРНЕЙМ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ИМЯ: {message.from_user.full_name}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info(f"📌 ЕСТЬ ЛИ ТЕКСТ: {bool(message.text)}")
        logger.info(f"📌 ТИП КОНТЕНТА: {message.content_type}")
        logger.info("=" * 60)
        
        # ============================================================
        # ИГНОРИРУЕМ СООБЩЕНИЯ БЕЗ ТЕКСТА
        # ============================================================
        if not message.text:
            logger.info("⏭️ ИГНОРИРУЕМ: сообщение без текста")
            return
        
        text = message.text
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        chat_id = message.chat.id
        chat_type = message.chat.type
        
        # ============================================================
        # КОМАНДА /chatid - ОТПРАВЛЯЕТ ID ЧАТА В ЛИЧКУ
        # ============================================================
        if text.lower() == '/chatid' or text.lower() == '!chatid':
            logger.info(f"🎯 ОБНАРУЖЕНА КОМАНДА /chatid от @{username} в чате {chat_id}")
            logger.info(f"📌 Тип чата: {chat_type}")
            
            # Формируем сообщение с информацией о чате
            chat_info = (
                f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
                f"🆔 ID ЧАТА: {chat_id}\n"
                f"📌 ТИП ЧАТА: {chat_type}\n"
                f"👤 ТВОЙ ID: {user_id}\n"
                f"👤 ЮЗЕРНЕЙМ: @{username}\n"
                f"👤 ИМЯ: {message.from_user.full_name}\n"
                f"📌 СООБЩЕНИЕ ИЗ: {chat_type}\n"
                f"🕐 ВРЕМЯ: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"✅ Бот видит этот чат!"
            )
            
            # ============================================================
            # ОТПРАВЛЯЕМ ID В ЛИЧКУ ПОЛЬЗОВАТЕЛЮ
            # ============================================================
            try:
                # Отправляем в ЛС пользователя
                await bot.send_message(
                    chat_id=user_id,
                    text=f"📩 Запрос /chatid из чата {chat_id}\n\n{chat_info}"
                )
                logger.info(f"✅ ID чата {chat_id} отправлен в ЛС пользователю @{username}")
                
                # Также отвечаем в чат (чтобы пользователь знал, что бот работает)
                await message.reply(
                    f"✅ Команда принята!\n"
                    f"📩 ID чата отправлен тебе в ЛС\n"
                    f"🆔 ID чата: {chat_id}"
                )
                logger.info(f"✅ Ответ отправлен в чат {chat_id}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке в ЛС: {e}")
                # Если не отправилось в ЛС, отвечаем в чате
                await message.reply(
                    f"⚠️ НЕ УДАЛОСЬ ОТПРАВИТЬ В ЛС\n\n"
                    f"🆔 ID ЧАТА: {chat_id}\n"
                    f"📌 ТИП: {chat_type}\n\n"
                    f"❌ Ошибка: {str(e)}"
                )
            
            return
        
        # ============================================================
        # КОМАНДА .whois
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info(f"🎯 КОМАНДА .whois от @{username} в чате {chat_id}")
            
            ip = text.replace('.whois', '').strip()
            logger.info(f"📌 IP после очистки: '{ip}'")
            
            if not ip:
                await message.reply("❌ Введите IP-адрес\n📌 Пример: .whois 8.8.8.8")
                return
            
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await message.reply("❌ Некорректный IP-адрес\n📌 Пример: 8.8.8.8")
                return
            
            logger.info(f"✅ IP валидный: {ip}")
            loading_msg = await message.reply("🔍 Поиск информации об IP...")
            
            result = await get_ip_info(ip)
            
            if result['success']:
                await loading_msg.edit_text(f"✅ ИНФОРМАЦИЯ ОБ IP\n\n{result['text']}")
            else:
                await loading_msg.edit_text(result['text'])
            
            logger.info(f"✅ IP {ip} проверен для @{username}")
            return
        
        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            await message.reply(
                "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                "/chatid - показать ID чата (отправит в ЛС)\n"
                ".whois IP - информация об IP\n"
                ".help - помощь\n"
                ".ping - проверка бота\n\n"
                "📌 Пример: .whois 8.8.8.8"
            )
            return
        
        # ============================================================
        # КОМАНДА .ping
        # ============================================================
        if text.lower() == '.ping':
            await message.reply(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")
            return
        
        # ============================================================
        # КОМАНДА НЕ РАСПОЗНАНА
        # ============================================================
        logger.info(f"⏭️ Команда не распознана: '{text}'")
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В HANDLE_MESSAGES: {e}")
        logger.error(traceback.format_exc())
        try:
            await message.reply(f"❌ Ошибка: {str(e)}")
        except:
            pass

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        logger.info(f"👤 Пользователь @{username} (ID: {user_id}) запустил бота (команда /start)")
        
        await message.answer(
            "🤖 БОТ АКТИВЕН\n\n"
            "📌 КОМАНДЫ:\n\n"
            "/chatid - показать ID чата (отправит в ЛС)\n"
            ".whois IP - информация об IP\n"
            ".help - помощь\n"
            ".ping - проверка бота\n\n"
            "💡 Пример: .whois 8.8.8.8"
        )
        logger.info(f"✅ Ответ на /start отправлен пользователю @{username}")
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")

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
            f"📌 Режим: Все чаты\n"
            f"📌 Команды: /chatid, .whois, .help, .ping"
        )
        await message.reply(stats)
        logger.info(f"✅ Статистика отправлена админу")
    except Exception as e:
        logger.error(f"❌ Ошибка в /status: {e}")

# ========== ЗАПУСК ==========
async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔥 БОТ ДЛЯ ЛИЧНЫХ ЧАТОВ ЗАПУЩЕН!")
        logger.info("🤖 Бот работает ВО ВСЕХ чатах")
        logger.info("📌 КОМАНДА /chatid - отправляет ID чата в ЛС")
        logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
        logger.info("📌 ДОСТУПНЫЕ КОМАНДЫ:")
        logger.info("   /chatid - ID чата в ЛС")
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
