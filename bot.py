import asyncio
import os
import sys
import logging
import re
import requests
import random
import json
import base64
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ (ЗАТКНУЛИ СПАМ) ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ОТКЛЮЧАЕМ СПАМ ОТ AIOGRAM
logging.getLogger('aiogram.dispatcher').setLevel(logging.WARNING)
logging.getLogger('aiogram.event').setLevel(logging.WARNING)
logging.getLogger('aiogram.client.session.aiohttp').setLevel(logging.WARNING)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ Токен не найден!")
    sys.exit(1)

if not GITHUB_TOKEN:
    logger.warning("⚠️ GITHUB_TOKEN не найден! Данные будут сохраняться локально.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== НАСТРОЙКИ GITHUB ==========
REPO_OWNER = "GrifMcPo"
REPO_NAME = "TelegramBotFAKEDDOSFAKEFAKEFAKE"
BRANCH = "main"
FILES = {
    "users": "users.json",
    "stats": "stats.json"
}

# ========== GITHUB API ФУНКЦИИ ==========
def get_github_headers():
    return {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }

def get_file_from_github(filename):
    try:
        if not GITHUB_TOKEN:
            return None, None
            
        url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}'
        headers = get_github_headers()
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            return json.loads(content), data['sha']
        elif response.status_code == 404:
            logger.info(f"📄 Файл {filename} не найден, будет создан новый")
            return None, None
        else:
            logger.error(f"❌ Ошибка получения {filename}: {response.status_code}")
            return None, None
    except Exception as e:
        logger.error(f"❌ Ошибка получения {filename}: {e}")
        return None, None

def save_file_to_github(filename, data, message):
    try:
        if not GITHUB_TOKEN:
            logger.warning("⚠️ Нет GITHUB_TOKEN, сохраняю локально")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
            
        url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}'
        headers = get_github_headers()
        
        existing, sha = get_file_from_github(filename)
        
        content = json.dumps(data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            'message': message,
            'content': encoded,
            'branch': BRANCH
        }
        
        if sha:
            payload['sha'] = sha
        
        response = requests.put(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Файл {filename} сохранен в GitHub")
            return True
        else:
            logger.error(f"❌ Ошибка сохранения {filename}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения {filename}: {e}")
        return False

def load_data():
    users_data = {}
    stats_data = {"total_commands": 0, "total_connections": 0, "users": {}}
    
    if GITHUB_TOKEN:
        logger.info("📥 Загрузка данных из GitHub...")
        users, _ = get_file_from_github(FILES["users"])
        if users:
            users_data = users
            logger.info(f"✅ Загружено {len(users_data)} пользователей из GitHub")
        
        stats, _ = get_file_from_github(FILES["stats"])
        if stats:
            stats_data = stats
            logger.info(f"✅ Загружена статистика из GitHub: {stats_data.get('total_commands', 0)} команд")
    else:
        logger.info("📥 Загрузка данных из локальных файлов...")
        try:
            if os.path.exists(FILES["users"]):
                with open(FILES["users"], 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    logger.info(f"✅ Загружено {len(users_data)} пользователей из локального файла")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локального users.json: {e}")
        
        try:
            if os.path.exists(FILES["stats"]):
                with open(FILES["stats"], 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
                    logger.info(f"✅ Загружена статистика из локального файла")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки локального stats.json: {e}")
    
    return users_data, stats_data

def save_data(users_data, stats_data, message="📊 Update data"):
    with open(FILES["users"], 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)
    
    with open(FILES["stats"], 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)
    
    logger.info("✅ Данные сохранены локально")
    
    if GITHUB_TOKEN:
        save_file_to_github(FILES["users"], users_data, f"📊 Update users - {get_msk_time()}")
        save_file_to_github(FILES["stats"], stats_data, f"📊 Update stats - {get_msk_time()}")

users_data, stats_data = load_data()
message_cache = {}

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

def get_spam_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔥 Троллинг спам", callback_data="spam_troll")],
        [InlineKeyboardButton(text="⏳ В разработке", callback_data="spam_dev")],
        [InlineKeyboardButton(text="⏳ В разработке", callback_data="spam_dev2")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

INSULTS = [
    "хахах что ты пидорасина в себя поверил?",
    "Сколько твоя мамка в час берет? или бесплатно ха-ха",
    "Что ты плакать мамульке побежишь?",
    "Ты же как ныть нихуя не умеешь пидорас толстый",
    "ной ной своей мамке ты просто не знаешь что я ее ебал",
    "Ты такой жалкий, что даже бомжи тебя жалеют!",
    "Твоя мамаша настолько толстая, что у нее свой гравитационный пояс!",
    "Ты настолько тупой, что даже 2+2 не можешь посчитать!",
    "Твой папаша настолько ленивый, что даже дышит через раз!",
    "Ты такой никчемный, что даже интернет тебя не хочет!"
]

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

async def send_to_chat(chat_id: int, text: str, connection_id: str, reply_markup=None):
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            business_connection_id=connection_id,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")
        return None

# =====================================================================
# ОБРАБОТЧИК ВСЕХ ОБНОВЛЕНИЙ
# =====================================================================
@dp.update()
async def handle_all_updates(update: types.Update):
    try:
        if update.business_connection:
            connection = update.business_connection
            if connection.user:
                user_id = connection.user.id
                username = connection.user.username or "Нет юзернейма"
                first_name = connection.user.first_name or "Неизвестно"
                now = get_msk_time()
                
                logger.info("=" * 60)
                logger.info("🔗 ПОДКЛЮЧЕНИЕ К БИЗНЕС-АККАУНТУ!")
                logger.info(f"📌 ID подключения: {connection.id}")
                logger.info(f"👤 ПОЛЬЗОВАТЕЛЬ: @{username} (ID: {user_id})")
                logger.info(f"🕐 ВРЕМЯ: {now}")
                logger.info("=" * 60)
                
                stats_data["total_connections"] += 1
                if str(user_id) not in stats_data["users"]:
                    stats_data["users"][str(user_id)] = {"commands": 0}
                
                users_data[str(user_id)] = {
                    "username": username,
                    "first_name": first_name,
                    "connected_at": now,
                    "last_active": now,
                    "connection_id": connection.id
                }
                
                save_data(users_data, stats_data, f"🔗 New connection: @{username}")
                
                await bot.send_message(
                    chat_id=user_id,
                    text=f"✅ БОТ АКТИВЕН!\n\n"
                         f"👤 Вы подключены к боту!\n"
                         f"🆔 Ваш ID: {user_id}\n"
                         f"🕐 Время: {now} (МСК)\n"
                         f"📌 Команды работают для вас!\n\n"
                         f"🔥 Введите .inf для справки."
                )
            return

        if update.business_message:
            message = update.business_message
            await handle_business_message(message)
            return

    except Exception as e:
        logger.error(f"❌ Ошибка в handle_all_updates: {e}")

# =====================================================================
# ОБРАБОТЧИК БИЗНЕС-СООБЩЕНИЙ
# =====================================================================
async def handle_business_message(message: types.Message):
    try:
        logger.info("=" * 60)
        logger.info("📩 НОВОЕ СООБЩЕНИЕ ИЗ БИЗНЕС-ЧАТА")
        logger.info(f"📌 ОТ: @{message.from_user.username or 'Нет'}")
        logger.info(f"📌 ID ПОЛЬЗОВАТЕЛЯ: {message.from_user.id}")
        logger.info(f"📌 ID ЧАТА: {message.chat.id}")
        logger.info(f"📌 ТЕКСТ: {message.text}")
        logger.info("=" * 60)

        user_id = message.from_user.id
        chat_id = message.chat.id
        connection_id = message.business_connection_id

        if str(user_id) not in users_data:
            logger.info(f"⛔ ИГНОР: @{message.from_user.username} (нет в users.json)")
            return

        if not message.text:
            return

        text = message.text
        message_id = message.message_id

        users_data[str(user_id)]["last_active"] = get_msk_time()
        save_data(users_data, stats_data, f"🔄 Activity: @{message.from_user.username}")

        # .inf
        if text.lower() == '.inf':
            logger.info("🎯 .inf")
            stats_data["total_commands"] += 1
            stats_data["users"][str(user_id)]["commands"] += 1
            save_data(users_data, stats_data, f"📊 Command: .inf by @{message.from_user.username}")
            
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(
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

        # .spam
        if text.lower().startswith('.spam') and not text.lower().startswith('.spams'):
            logger.info("🎯 .spam")
            
            stats_data["total_commands"] += 1
            stats_data["users"][str(user_id)]["commands"] += 1
            save_data(users_data, stats_data, f"📊 Command: .spam by @{message.from_user.username}")
            
            parts = text.split(maxsplit=2)
            
            if len(parts) < 3:
                await send_to_chat(
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
                await send_to_chat(
                    chat_id,
                    "❌ Количество должно быть числом!\n\n"
                    "Пример: .spam 5 Привет всем!",
                    connection_id
                )
                return
            
            if count < 1:
                await send_to_chat(chat_id, "❌ Количество должно быть больше 0!", connection_id)
                return
            
            if count > 100:
                await send_to_chat(chat_id, "❌ Максимум 100 сообщений за раз!", connection_id)
                return
            
            await delete_business_message(chat_id, message_id, connection_id)
            
            await send_to_chat(
                chat_id=chat_id,
                text=f"🔥 Начинаю спам!\n📊 {count} сообщений\n📝 Текст: {spam_text}",
                connection_id=connection_id
            )
            
            for i in range(1, count + 1):
                await send_to_chat(
                    chat_id=chat_id,
                    text=f"{i}. {spam_text}",
                    connection_id=connection_id
                )
                await asyncio.sleep(0.3)
            
            await send_to_chat(
                chat_id=chat_id,
                text=f"✅ Спам завершен! Отправлено {count} сообщений.",
                connection_id=connection_id
            )
            
            logger.info(f"✅ Спам {count} раз отправлен")
            return

        # .spams
        if text.lower() == '.spams':
            logger.info("🎯 .spams")
            stats_data["total_commands"] += 1
            stats_data["users"][str(user_id)]["commands"] += 1
            save_data(users_data, stats_data, f"📊 Command: .spams by @{message.from_user.username}")
            
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(
                chat_id=chat_id,
                text="🔥 Спам-меню открыто!\n\nВыберите какой спам вам нужен:",
                connection_id=connection_id,
                reply_markup=get_spam_keyboard()
            )
            return

        # .whois
        if text.lower().startswith('.whois'):
            logger.info("🎯 .whois")
            stats_data["total_commands"] += 1
            stats_data["users"][str(user_id)]["commands"] += 1
            save_data(users_data, stats_data, f"📊 Command: .whois by @{message.from_user.username}")
            
            parts = text.split()
            if len(parts) < 3:
                await send_to_chat(
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
                    await send_to_chat(chat_id, f"❌ Некорректный IP: {target}\n📌 Пример: 8.8.8.8", connection_id)
                    return
                
                await delete_business_message(chat_id, message_id, connection_id)
                result = await get_ip_info(target)
                await send_to_chat(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}", connection_id)
                logger.info(f"✅ IP {target} проверен")
                return
            
            elif command_type == 'number':
                await delete_business_message(chat_id, message_id, connection_id)
                result = await get_phone_info(target)
                await send_to_chat(chat_id, result['text'] if result['success'] else f"❌ Ошибка: {result['text']}", connection_id)
                logger.info(f"✅ Номер {target} проверен")
                return
            
            else:
                await send_to_chat(
                    chat_id,
                    "❌ Неизвестный тип\n\n"
                    "📌 Доступные типы:\n"
                    ".whois ip [IP] - пробив по IP\n"
                    ".whois number [НОМЕР] - пробив по номеру",
                    connection_id
                )
            return

        # .ping
        if text.lower() == '.ping':
            logger.info("🎯 .ping")
            stats_data["total_commands"] += 1
            stats_data["users"][str(user_id)]["commands"] += 1
            save_data(users_data, stats_data, f"📊 Command: .ping by @{message.from_user.username}")
            
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(
                chat_id=chat_id,
                text=f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}",
                connection_id=connection_id
            )
            logger.info("✅ Ответ отправлен")
            return

        # /chatid
        if text.lower() == '/chatid':
            logger.info("🎯 /chatid")
            stats_data["total_commands"] += 1
            stats_data["users"][str(user_id)]["commands"] += 1
            save_data(users_data, stats_data, f"📊 Command: /chatid by @{message.from_user.username}")
            
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(
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

# =====================================================================
# ОБРАБОТЧИК ОБЫЧНЫХ СООБЩЕНИЙ
# =====================================================================
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🤖 БОТ АКТИВЕН\n\n"
        "📌 Введи .inf для справки\n\n"
        "📌 КОМАНДЫ:\n"
        ".whois ip [IP] - пробив по IP\n"
        ".whois number [НОМЕР] - пробив по номеру\n"
        ".spam [Кол-во] [Текст] - спам\n"
        ".spams - спам-меню\n"
        ".ping - проверка\n"
        ".inf - справка"
    )

@dp.message()
async def handle_private_message(message: types.Message):
    try:
        if not message.text:
            return

        text = message.text
        user_id = message.from_user.id

        if text.lower() == '/start':
            await start_command(message)
            return

        if text.lower() == '.inf':
            await message.answer(
                "📚 Справка по командам\n\n"
                "🐢 ПРОБИВ\n"
                ".whois ip [IP] - Пробив по IP-адресу\n"
                ".whois number [НОМЕР] - Пробив по номеру телефона\n\n"
                "🔥 СПАМ\n"
                ".spam [Кол-во] [Текст] - Спам вашим сообщением\n"
                ".spams - Открыть спам-меню\n\n"
                "⚡ ДРУГОЕ\n"
                ".ping - Проверка работы бота\n"
                ".inf - Эта справка"
            )
            return

        if text.lower() == '.ping':
            await message.answer(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")
            return

        if text.lower() == '/chatid':
            await message.answer(f"🆔 Ваш ID: {user_id}")
            return

        if text.startswith('.'):
            await message.answer(
                "⚠️ Эта команда работает только в чатах с собеседниками!\n\n"
                "📌 Напиши команду в личном чате с собеседником, где подключен бот."
            )
            return

        await message.answer(
            "❓ Неизвестная команда\n\n"
            "📌 Введи .inf для справки"
        )

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")
        import traceback
        logger.error(traceback.format_exc())

# =====================================================================
# ОБРАБОТЧИК КНОПОК
# =====================================================================
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
            
            await send_to_chat(
                chat_id=chat_id,
                text="🔥 Начинаю троллинг спам...\n\n💬 Отправляю 10 оскорблений!",
                connection_id=connection_id
            )
            
            for i, insult in enumerate(INSULTS, 1):
                await send_to_chat(
                    chat_id=chat_id,
                    text=f"{i}. {insult}",
                    connection_id=connection_id
                )
                await asyncio.sleep(0.5)
            
            await send_to_chat(
                chat_id=chat_id,
                text="✅ Спам завершен! Все 10 оскорблений отправлены.",
                connection_id=connection_id
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

# =====================================================================
# ЗАПУСК С АВТОУБИЙСТВОМ КОНФЛИКТОВ
# =====================================================================
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info(f"📌 Загружено пользователей: {len(users_data)}")
    logger.info(f"📌 Всего команд: {stats_data.get('total_commands', 0)}")
    logger.info(f"📌 Время: {get_msk_time()} (МСК)")
    if GITHUB_TOKEN:
        logger.info("📌 GitHub API: ВКЛЮЧЕН (данные сохраняются в репозиторий)")
    else:
        logger.warning("📌 GitHub API: ОТКЛЮЧЕН (данные только локально)")
    logger.info("=" * 60)
    
    # Запускаем бота — если конфликт, просто игнорируем
    try:
        await dp.start_polling(bot)
    except Exception as e:
        if "Conflict" in str(e):
            logger.warning("⚠️ Конфликт, но бот уже работает! Игнорируем...")
            # Всё равно пытаемся запустить
            await dp.start_polling(bot)
        else:
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)
