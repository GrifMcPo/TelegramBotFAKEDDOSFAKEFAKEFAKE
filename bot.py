import asyncio
import os
import sys
import logging
import re
import requests
import random
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types.business_connection import BusinessConnection
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.business_messages_deleted import BusinessMessagesDeleted

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

# ========== ХРАНИЛИЩЕ ПОСЛЕДНИХ СООБЩЕНИЙ ==========
last_messages = {}  # {chat_id: {message_id: (text, from_user)}}

# ========== КЛАВИАТУРА ==========
def get_spam_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔥 Троллинг спам", callback_data="spam_troll")],
        [InlineKeyboardButton(text="⏳ В разработке", callback_data="spam_dev")],
        [InlineKeyboardButton(text="⏳ В разработке", callback_data="spam_dev2")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

# ========== УДАЛЕНИЕ ЧЕРЕЗ ПРЯМОЙ API-ЗАПРОС ==========
async def delete_business_message(chat_id: int, message_id: int, connection_id: str):
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteBusinessMessages'
        payload = {
            "business_connection_id": connection_id,
            "message_ids": [message_id]
        }
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"🗑️ Сообщение {message_id} удалено через Business API")
            return True
        else:
            logger.warning(f"⚠️ Ошибка удаления: {result.get('description', 'Неизвестная ошибка')}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить через Business API: {e}")
        return False

# ========== ОТПРАВКА В БИЗНЕС-ЧАТ ==========
async def send_business_message(chat_id: int, text: str, connection_id: str = None, reply_markup=None):
    try:
        if connection_id:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                business_connection_id=connection_id,
                reply_markup=reply_markup
            )
        else:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
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

# ========== ОБРАБОТЧИК УДАЛЕННЫХ СООБЩЕНИЙ ==========
@dp.business_messages_deleted()
async def handle_business_messages_deleted(event: BusinessMessagesDeleted):
    try:
        chat_id = event.chat_id
        message_ids = event.message_ids
        
        logger.info("=" * 60)
        logger.info("🗑️ ОБНАРУЖЕНЫ УДАЛЕННЫЕ СООБЩЕНИЯ")
        logger.info(f"📌 ID ЧАТА: {chat_id}")
        logger.info(f"📌 КОЛИЧЕСТВО: {len(message_ids)}")
        logger.info("=" * 60)
        
        # Получаем информацию о чате
        try:
            chat = await bot.get_chat(chat_id)
            chat_username = chat.username or "Неизвестно"
            chat_title = chat.title or "Личный чат"
        except:
            chat_username = "Неизвестно"
            chat_title = "Личный чат"
        
        # Для каждого удаленного сообщения
        for msg_id in message_ids:
            # Пытаемся найти сообщение в кеше
            if chat_id in last_messages and msg_id in last_messages[chat_id]:
                msg_text, from_user = last_messages[chat_id][msg_id]
                
                # Формируем отчет
                report = (
                    f"⚠️ ЗАФИКСИРОВАНО УДАЛЕННОЕ СООБЩЕНИЕ!\n\n"
                    f"🆔 ID ЧАТА: {chat_id}\n"
                    f"👤 С КЕМ В ЧАТЕ: @{from_user or 'Неизвестно'}\n"
                    f"📝 ЧАТ: {chat_title}\n\n"
                    f"📩 СООБЩЕНИЕ КОТОРОЕ УДАЛИЛИ:\n"
                    f"────────────────────\n"
                    f"{msg_text if msg_text else '[Медиафайл]'}\n"
                    f"────────────────────\n\n"
                    f"🕐 ВРЕМЯ УДАЛЕНИЯ: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                )
                
                # Отправляем в ЛС админу
                try:
                    await bot.send_message(chat_id=ADMIN_ID, text=report)
                    logger.info(f"✅ Отчет об удалении отправлен админу")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки отчета: {e}")
            else:
                logger.info(f"⚠️ Сообщение {msg_id} не найдено в кеше")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_business_messages_deleted: {e}")
        import traceback
        logger.error(traceback.format_exc())

# ========== ОБРАБОТЧИК НАЖАТИЯ КНОПОК ==========
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    try:
        data = callback.data
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id
        connection_id = callback.business_connection_id
        
        logger.info(f"🎯 Нажата кнопка: {data} от @{callback.from_user.username}")
        
        if data == "spam_troll":
            await delete_business_message(chat_id, message_id, connection_id)
            
            await bot.send_message(
                chat_id=chat_id,
                text="🔥 Начинаю троллинг спам...\n\n💬 Отправляю 10 оскорблений!",
                business_connection_id=connection_id
            )
            
            for i, insult in enumerate(INSULTS, 1):
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"{i}. {insult}",
                    business_connection_id=connection_id
                )
                await asyncio.sleep(0.5)
            
            await bot.send_message(
                chat_id=chat_id,
                text="✅ Спам завершен! Все 10 оскорблений отправлены.",
                business_connection_id=connection_id
            )
            
            await callback.answer()
            return
        
        if data in ["spam_dev", "spam_dev2"]:
            await callback.answer("⏳ Функция в разработке!", show_alert=True)
            return
        
    except Exception as e:
        logger.error(f"❌ Ошибка в callback: {e}")
        import traceback
        logger.error(traceback.format_exc())

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
            # Сохраняем медиа в кеш
            chat_id = message.chat.id
            msg_id = message.message_id
            from_user = message.from_user.username or "Неизвестно"
            
            if chat_id not in last_messages:
                last_messages[chat_id] = {}
            last_messages[chat_id][msg_id] = ("[Медиафайл]", from_user)
            
            # Ограничиваем кеш
            if len(last_messages[chat_id]) > 100:
                oldest = min(last_messages[chat_id].keys())
                del last_messages[chat_id][oldest]
            
            return

        text = message.text
        chat_id = message.chat.id
        message_id = message.message_id
        connection_id = message.business_connection_id
        from_user = message.from_user.username or "Неизвестно"

        # ============================================================
        # СОХРАНЯЕМ СООБЩЕНИЕ В КЕШ
        # ============================================================
        if chat_id not in last_messages:
            last_messages[chat_id] = {}
        last_messages[chat_id][message_id] = (text, from_user)
        
        # Ограничиваем кеш (максимум 100 сообщений на чат)
        if len(last_messages[chat_id]) > 100:
            oldest = min(last_messages[chat_id].keys())
            del last_messages[chat_id][oldest]

        # ============================================================
        # .inf - СПРАВКА
        # ============================================================
        if text.lower() == '.inf':
            logger.info("🎯 .inf")
            
            await delete_business_message(chat_id, message_id, connection_id)
            
            await send_business_message(
                chat_id=chat_id,
                text=(
                    "📚 Справка по командам\n\n"
                    "👤 Ваша подписка: LEADER\n\n"
                    "📌 Формат команд: .команда - описание\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🐢 ПРОБИВ\n\n"
                    "> .whois ip [IP] - Пробив по IP-адресу\n"
                    "> .whois number [НОМЕР] - Пробив по номеру телефона\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🔥 СПАМ\n\n"
                    "> .spam [Кол-во] [Текст] - Спам вашим сообщением\n"
                    "> .spams - Открыть спам-меню\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "⚡ ДРУГОЕ\n\n"
                    "> .ping - Проверка работы бота\n"
                    "> .inf - Эта справка"
                ),
                connection_id=connection_id
            )
            return

        # ============================================================
        # .spam [КОЛ-ВО] [ТЕКСТ]
        # ============================================================
        if text.lower().startswith('.spam') and not text.lower().startswith('.spams'):
            logger.info("🎯 .spam")
            
            parts = text.split(maxsplit=2)
            
            if len(parts) < 3:
                await send_business_message(
                    chat_id,
                    "❌ Неправильный формат\n\n"
                    "📌 .spam [Кол-во] [Текст]\n\n"
                    "Пример: .spam 5 Привет всем!",
                    connection_id
                )
                return
            
            try:
                count = int(parts[1])
                spam_text = parts[2]
            except ValueError:
                await send_business_message(
                    chat_id,
                    "❌ Количество должно быть числом!\n\n"
                    "Пример: .spam 5 Привет всем!",
                    connection_id
                )
                return
            
            if count < 1:
                await send_business_message(chat_id, "❌ Количество должно быть больше 0!", connection_id)
                return
            
            if count > 100:
                await send_business_message(chat_id, "❌ Максимум 100 сообщений за раз!", connection_id)
                return
            
            await delete_business_message(chat_id, message_id, connection_id)
            
            await send_business_message(
                chat_id=chat_id,
                text=f"🔥 Начинаю спам!\n📊 {count} сообщений\n📝 Текст: {spam_text}",
                connection_id=connection_id
            )
            
            for i in range(1, count + 1):
                await send_business_message(
                    chat_id=chat_id,
                    text=f"{i}. {spam_text}",
                    connection_id=connection_id
                )
                await asyncio.sleep(0.3)
            
            await send_business_message(
                chat_id=chat_id,
                text=f"✅ Спам завершен! Отправлено {count} сообщений.",
                connection_id=connection_id
            )
            
            logger.info(f"✅ Спам {count} раз отправлен")
            return

        # ============================================================
        # .spams - СПАМ-МЕНЮ
        # ============================================================
        if text.lower() == '.spams':
            logger.info("🎯 .spams")
            
            await delete_business_message(chat_id, message_id, connection_id)
            
            await send_business_message(
                chat_id=chat_id,
                text=(
                    "🔥 Спам-меню открыто!\n\n"
                    "Выберите какой спам вам нужен:"
                ),
                connection_id=connection_id,
                reply_markup=get_spam_keyboard()
            )
            return

        # ============================================================
        # .whois
        # ============================================================
        if text.lower().startswith('.whois'):
            logger.info("🎯 .whois")
            
            parts = text.split()
            if len(parts) < 3:
                await send_business_message(
                    chat_id,
                    "❌ Неправильный формат\n\n"
                    "📌 .whois ip [IP] - пробив по IP\n"
                    "📌 .whois number [НОМЕР] - пробив по номеру\n\n"
                    "Примеры:\n"
                    ".whois ip 8.8.8.8\n"
                    ".whois number 89001234567",
                    connection_id
                )
                return
            
            command_type = parts[1].lower()
            target = ' '.join(parts[2:])
            
            if command_type == 'ip':
                ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
                if not re.match(ip_pattern, target):
                    await send_business_message(chat_id, f"❌ Некорректный IP: {target}\n📌 Пример: 8.8.8.8", connection_id)
                    return
                
                await delete_business_message(chat_id, message_id, connection_id)
                
                result = await get_ip_info(target)
                await send_business_message(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}", connection_id)
                logger.info(f"✅ IP {target} проверен")
                return
            
            elif command_type == 'number':
                await delete_business_message(chat_id, message_id, connection_id)
                
                result = await get_phone_info(target)
                await send_business_message(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}", connection_id)
                logger.info(f"✅ Номер {target} проверен")
                return
            
            else:
                await send_business_message(
                    chat_id,
                    "❌ Неизвестный тип\n\n"
                    "📌 Доступные типы:\n"
                    ".whois ip [IP] - пробив по IP\n"
                    ".whois number [НОМЕР] - пробив по номеру",
                    connection_id
                )
            return

        # ============================================================
        # .ping
        # ============================================================
        if text.lower() == '.ping':
            logger.info("🎯 .ping")
            
            await delete_business_message(chat_id, message_id, connection_id)
            
            await send_business_message(
                chat_id=chat_id,
                text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}",
                connection_id=connection_id
            )
            
            logger.info("✅ Ответ отправлен")
            return

        # ============================================================
        # /chatid
        # ============================================================
        if text.lower() == '/chatid':
            logger.info("🎯 /chatid")
            
            await delete_business_message(chat_id, message_id, connection_id)
            
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
        ".spam [Кол-во] [Текст] - спам\n"
        ".spams - спам-меню\n"
        ".ping - проверка\n"
        ".inf - справка\n\n"
        "🔥 Бот отслеживает УДАЛЕННЫЕ сообщения!"
    )

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info("📌 Бот отслеживает удаленные сообщения")
    logger.info("📌 Отчеты приходят в ЛС админу")
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
