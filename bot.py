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
logger.info("🚀 ЗАПУСК БОТА ДЛЯ РЕДАКТИРОВАНИЯ СООБЩЕНИЙ")
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

# ========== ОСНОВНОЙ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ==========
@dp.message()
async def handle_messages(message: types.Message):
    try:
        # ============================================================
        # МОЩНОЕ ЛОГИРОВАНИЕ
        # ============================================================
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ")
        logger.info(f"📌 ID СООБЩЕНИЯ: {message.message_id}")
        logger.info(f"📌 ТИП ЧАТА: {message.chat.type}")
        logger.info(f"📌 ID ЧАТА: {message.chat.id}")
        logger.info(f"📌 ID ПОЛЬЗОВАТЕЛЯ: {message.from_user.id}")
        logger.info(f"📌 ЮЗЕРНЕЙМ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ИМЯ: {message.from_user.full_name}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
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
        message_id = message.message_id
        
        # ============================================================
        # КОМАНДА .whois - РЕДАКТИРУЕТ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info(f"🎯 КОМАНДА .whois от @{username} в чате {chat_id}")
            
            ip = text.replace('.whois', '').strip()
            logger.info(f"📌 IP после очистки: '{ip}'")
            
            if not ip:
                # Если IP не указан, редактируем сообщение с ошибкой
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="❌ ОШИБКА\n\nВведите IP-адрес\n📌 Пример: .whois 8.8.8.8"
                )
                logger.info("✅ Сообщение отредактировано: IP не указан")
                return
            
            # Валидация IP
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(ip_pattern, ip):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ НЕКОРРЕКТНЫЙ IP\n\nВведено: {ip}\n📌 Пример: 8.8.8.8"
                )
                logger.info(f"✅ Сообщение отредактировано: некорректный IP {ip}")
                return
            
            logger.info(f"✅ IP валидный: {ip}")
            
            # ============================================================
            # РЕДАКТИРУЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ
            # ============================================================
            # Сначала меняем на "загрузка"
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🔍 ПОИСК ИНФОРМАЦИИ ОБ IP {ip}..."
            )
            logger.info(f"📝 Сообщение отредактировано: загрузка")
            
            # Получаем данные
            result = await get_ip_info(ip)
            logger.info(f"📥 Получен результат от API: success={result['success']}")
            
            # Финальное редактирование
            if result['success']:
                final_text = result['text']
                logger.info("📤 Отправка успешного результата")
            else:
                final_text = f"❌ ОШИБКА\n\n{result['text']}"
                logger.warning("📤 Отправка сообщения об ошибке")
            
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=final_text
            )
            logger.info(f"✅ Сообщение отредактировано финальным результатом")
            logger.info(f"📌 ИТОГ: IP {ip} проверен для @{username} в чате {chat_id}")
            return
        
        # ============================================================
        # КОМАНДА .help
        # ============================================================
        if text.lower() == '.help':
            logger.info(f"📖 ПОКАЗ HELP для @{username}")
            help_text = (
                "🤖 ДОСТУПНЫЕ КОМАНДЫ\n\n"
                ".whois IP - информация об IP (редактирует сообщение)\n"
                ".help - помощь\n"
                ".ping - проверка\n\n"
                "📌 Пример: .whois 8.8.8.8\n\n"
                "🔥 Команда РЕДАКТИРУЕТ твое сообщение!"
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
        # КОМАНДА /chatid
        # ============================================================
        if text.lower() == '/chatid':
            logger.info(f"🎯 КОМАНДА /chatid от @{username} в чате {chat_id}")
            
            chat_info = (
                f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
                f"🆔 ID ЧАТА: {chat_id}\n"
                f"📌 ТИП ЧАТА: {message.chat.type}\n"
                f"👤 ТВОЙ ID: {user_id}\n"
                f"👤 ЮЗЕРНЕЙМ: @{username}\n"
                f"🕐 ВРЕМЯ: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"✅ Бот видит этот чат!"
            )
            
            try:
                # Отправляем в ЛС пользователя
                await bot.send_message(
                    chat_id=user_id,
                    text=f"📩 Запрос /chatid из чата {chat_id}\n\n{chat_info}"
                )
                logger.info(f"✅ ID чата {chat_id} отправлен в ЛС пользователю @{username}")
                
                # Редактируем сообщение в чате
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ ID чата отправлен тебе в ЛС\n🆔 ID: {chat_id}"
                )
                logger.info(f"✅ Сообщение отредактировано")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке в ЛС: {e}")
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"⚠️ НЕ УДАЛОСЬ ОТПРАВИТЬ В ЛС\n\n🆔 ID ЧАТА: {chat_id}\n❌ Ошибка: {str(e)}"
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
            await message.reply(f"❌ Ошибка: {str(e)}")
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
            "📌 КОМАНДЫ РЕДАКТИРУЮТ ТВОИ СООБЩЕНИЯ!\n\n"
            ".whois IP - информация об IP (редактирует сообщение)\n"
            ".help - помощь\n"
            ".ping - проверка\n"
            "/chatid - ID чата в ЛС\n\n"
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
            f"📌 Режим: Редактирование сообщений\n"
            f"📌 Команды: .whois (редактирует), .help, .ping, /chatid"
        )
        await message.reply(stats)
        logger.info(f"✅ Статистика отправлена админу")
    except Exception as e:
        logger.error(f"❌ Ошибка в /status: {e}")

# ========== ЗАПУСК ==========
async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔥 БОТ ДЛЯ РЕДАКТИРОВАНИЯ СООБЩЕНИЙ ЗАПУЩЕН!")
        logger.info("🤖 Бот РЕДАКТИРУЕТ твои сообщения в чатах!")
        logger.info("📌 КОМАНДА .whois - заменяет сообщение на информацию об IP")
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
