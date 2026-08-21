import asyncio
import os
import sys
import json
import base64
import logging
import re
import requests
import ipaddress
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import BusinessConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8857252828"))

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LOGS_FILE = "logs.json"
BLACKLIST_FILE = "blacklist.json"

user_data = {}
business_connections = {}

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

# ========== ЧЕРНЫЙ СПИСОК ==========
def load_blacklist():
    try:
        if os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_blacklist_local(blacklist):
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def add_to_blacklist(user_id, reason, admin_id):
    blacklist = load_blacklist()
    blacklist[str(user_id)] = {
        "reason": reason,
        "added_by": admin_id,
        "added_at": get_msk_time()
    }
    save_blacklist_local(blacklist)
    return True

def remove_from_blacklist(user_id):
    blacklist = load_blacklist()
    if str(user_id) in blacklist:
        del blacklist[str(user_id)]
        save_blacklist_local(blacklist)
        return True
    return False

def is_blacklisted(user_id):
    blacklist = load_blacklist()
    return str(user_id) in blacklist

def get_blacklist_reason(user_id):
    blacklist = load_blacklist()
    return blacklist.get(str(user_id), {}).get("reason", "Не указана")

# ========== ЛОГИ ==========
def save_log_local(log_entry):
    try:
        logs = []
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        logs.append(log_entry)
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def save_log(log_entry):
    save_log_local(log_entry)

# ========== УДАЛЕНИЕ ==========
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
            logger.info(f"🗑️ Сообщение {message_id} удалено")
            return True
        return False
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить: {e}")
        return False

# ========== ОТПРАВКА В БИЗНЕС-ЧАТ ==========
async def send_to_business_chat(chat_id: int, text: str, connection_id: str, reply_markup=None):
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

# ========== РЕДАКТИРОВАНИЕ В БИЗНЕС-ЧАТЕ ==========
async def edit_business_message(chat_id: int, message_id: int, text: str, connection_id: str):
    """Редактирует сообщение в бизнес-чате через прямой API-запрос"""
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText'
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "business_connection_id": connection_id
        }
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        if result.get('ok'):
            logger.info(f"✅ Сообщение {message_id} отредактировано")
            return True
        else:
            logger.warning(f"⚠️ Ошибка редактирования: {result.get('description')}")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отредактировать: {e}")
        return False

# ========== РЕДАКТИРОВАНИЕ В ОБЫЧНОМ ЧАТЕ ==========
async def edit_normal_message(chat_id: int, message_id: int, text: str):
    """Редактирует сообщение в обычном чате через bot.edit_message_text"""
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text
        )
        return True
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отредактировать: {e}")
        return False

# ========== АНИМАЦИЯ ==========
async def show_animation(target, connection_id=None):
    """Показывает анимацию подключения"""
    
    # Отправляем первое сообщение
    if connection_id:
        msg = await send_to_business_chat(
            target,
            "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
            "📡 Сервер #1... ████░░░░░░ 40%\n"
            "📡 Сервер #2... ░░░░░░░░░░ 0%\n"
            "📡 Сервер #3... ░░░░░░░░░░ 0%\n"
            "📡 Сервер #4... ░░░░░░░░░░ 0%\n"
            "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
            "⏳ Ожидайте...",
            connection_id
        )
    else:
        msg = await target.answer(
            "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
            "📡 Сервер #1... ████░░░░░░ 40%\n"
            "📡 Сервер #2... ░░░░░░░░░░ 0%\n"
            "📡 Сервер #3... ░░░░░░░░░░ 0%\n"
            "📡 Сервер #4... ░░░░░░░░░░ 0%\n"
            "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
            "⏳ Ожидайте..."
        )
    
    await asyncio.sleep(0.5)
    
    # Редактируем — шаг 2
    if connection_id:
        await edit_business_message(
            target,
            msg.message_id,
            "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
            "📡 Сервер #1... ████████░░ 80%\n"
            "📡 Сервер #2... ██████░░░░ 60%\n"
            "📡 Сервер #3... ████░░░░░░ 40%\n"
            "📡 Сервер #4... ██░░░░░░░░ 20%\n"
            "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
            "⏳ Ожидайте...",
            connection_id
        )
    else:
        await edit_normal_message(target, msg.message_id,
            "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
            "📡 Сервер #1... ████████░░ 80%\n"
            "📡 Сервер #2... ██████░░░░ 60%\n"
            "📡 Сервер #3... ████░░░░░░ 40%\n"
            "📡 Сервер #4... ██░░░░░░░░ 20%\n"
            "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
            "⏳ Ожидайте..."
        )
    await asyncio.sleep(0.5)
    
    # Редактируем — шаг 3
    if connection_id:
        await edit_business_message(
            target,
            msg.message_id,
            "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
            "📡 Сервер #1... ██████████ 100% ✅\n"
            "📡 Сервер #2... ██████████ 100% ✅\n"
            "📡 Сервер #3... ████████░░ 80%\n"
            "📡 Сервер #4... ██████░░░░ 60%\n"
            "📡 Сервер #5... ████░░░░░░ 40%\n\n"
            "⏳ Ожидайте...",
            connection_id
        )
    else:
        await edit_normal_message(target, msg.message_id,
            "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
            "📡 Сервер #1... ██████████ 100% ✅\n"
            "📡 Сервер #2... ██████████ 100% ✅\n"
            "📡 Сервер #3... ████████░░ 80%\n"
            "📡 Сервер #4... ██████░░░░ 60%\n"
            "📡 Сервер #5... ████░░░░░░ 40%\n\n"
            "⏳ Ожидайте..."
        )
    await asyncio.sleep(0.5)
    
    # Редактируем — финал
    if connection_id:
        await edit_business_message(
            target,
            msg.message_id,
            "✅ ПОДКЛЮЧЕНИЕ ВЫПОЛНЕНО\n\n"
            "📊 Получение данных...\n"
            "⏳ Обработка информации...",
            connection_id
        )
    else:
        await edit_normal_message(target, msg.message_id,
            "✅ ПОДКЛЮЧЕНИЕ ВЫПОЛНЕНО\n\n"
            "📊 Получение данных...\n"
            "⏳ Обработка информации..."
        )
    await asyncio.sleep(0.5)
    
    return msg

# ========== ПРОБИВ IP ==========
async def probe_ip(ip: str):
    results = []
    success_count = 0
    
    sources = [
        {"name": "Сервер #1", "url": "http://ip-api.com/json/{}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query"},
        {"name": "Сервер #2", "url": "https://ipinfo.io/{}/json"},
        {"name": "Сервер #3", "url": "http://ipwhois.io/json/{}"},
        {"name": "Сервер #4", "url": "https://freegeoip.app/json/{}"},
        {"name": "Сервер #5", "url": "https://ipapi.co/{}/json"},
    ]
    
    for source in sources:
        try:
            url = source["url"].format(ip)
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                results.append({"source": source["name"], "data": data})
        except:
            pass
    
    return results, success_count

# ========== ПРОБИВ НОМЕРА ==========
async def probe_phone(phone: str):
    results = []
    success_count = 0
    local_data = None
    
    phone_clean = phone.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    
    try:
        parsed = phonenumbers.parse(phone_clean, None)
        if phonenumbers.is_valid_number(parsed):
            operator = carrier.name_for_number(parsed, "ru") or "Не определено"
            region = geocoder.description_for_number(parsed, "ru") or "Не определено"
            timezone_info = timezone.time_zones_for_number(parsed)
            phone_type = phonenumbers.number_type(parsed)
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            
            type_names = {0: "Неизвестный", 1: "Стационарный", 2: "Мобильный", 3: "Стационарный (набор)", 4: "VoIP", 5: "Личный номер", 6: "Универсальный", 7: "Pager"}
            
            local_data = {
                "formatted": formatted,
                "national": national,
                "operator": operator,
                "region": region,
                "timezone": ', '.join(timezone_info) if timezone_info else "Не определено",
                "type": type_names.get(phone_type, "Неизвестный"),
                "country_code": str(parsed.country_code)
            }
            results.append(local_data)
            success_count += 1
    except:
        pass
    
    return results, success_count, local_data

def analyze_ip_results(results):
    final = {"country": "Не определено", "region": "Не определено", "city": "Не определено", "isp": "Не определено", "org": "Не определено", "as": "Не определено", "timezone": "Не определено"}
    field_map = {"country": ["country", "country_name", "countryCode"], "region": ["region", "regionName", "region_name"], "city": ["city", "city_name"], "isp": ["isp", "org"], "org": ["org", "organization"], "as": ["as", "asn"], "timezone": ["timezone", "time_zone"]}
    values = {key: [] for key in final.keys()}
    
    for result in results:
        data = result.get("data", {})
        for field, aliases in field_map.items():
            for alias in aliases:
                if alias in data and data[alias]:
                    values[field].append(data[alias])
                    break
    
    from collections import Counter
    for field, vals in values.items():
        if vals:
            final[field] = Counter(vals).most_common(1)[0][0]
    
    return final

def analyze_phone_results(results, local_data):
    final = {"formatted": "Не определено", "national": "Не определено", "operator": "Не определено", "region": "Не определено", "timezone": "Не определено", "type": "Не определено", "country_code": "Не определено"}
    
    if local_data:
        for key in final.keys():
            if key in local_data:
                final[key] = local_data[key]
    
    return final

# ========== КЛАВИАТУРА ==========
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🌐 ПРОБИВ IP", callback_data="probe_ip")],
        [InlineKeyboardButton(text="📱 ПРОБИВ НОМЕРА", callback_data="probe_phone")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== BUSINESS CONNECTION ==========
@dp.business_connection()
async def handle_business_connection(connection: BusinessConnection):
    if connection.user:
        user_id = connection.user.id
        connection_id = connection.id
        username = connection.user.username or "Нет юзернейма"
        
        business_connections[str(user_id)] = connection_id
        
        logger.info(f"🔗 BUSINESS CONNECTION: @{username} (ID: {user_id})")
        
        user_data[user_id] = {
            "connection_id": connection_id,
            "username": username,
            "connected_at": get_msk_time()
        }
        
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ БОТ ПОДКЛЮЧЕН К БИЗНЕС-АККАУНТУ!\n\n"
                 f"🆔 ID: {user_id}\n"
                 f"📌 Теперь команды работают в чатах с собеседниками!\n"
                 f"🔥 Введите .help для списка команд"
        )

# ========== BUSINESS MESSAGE ==========
@dp.business_message()
async def handle_business_message(message: types.Message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        message_id = message.message_id
        connection_id = message.business_connection_id
        
        if not connection_id:
            connection_id = business_connections.get(str(user_id))
        
        if is_blacklisted(user_id):
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(
                chat_id,
                f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ БОТА!\n📌 Причина: {get_blacklist_reason(user_id)}",
                connection_id
            )
            return
        
        if not message.text:
            return
        
        text = message.text.strip()
        
        # .help
        if text.lower() == '.help':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(
                chat_id,
                "📚 СПИСОК КОМАНД\n\n"
                ".help - Эта справка\n"
                ".ping - Проверка бота\n"
                ".time - Текущее время\n"
                ".info - Информация о себе\n\n"
                "🔍 ПРОБИВ\n"
                ".whois ip [IP] - Пробив по IP\n"
                ".whois number [НОМЕР] - Пробив по номеру\n\n"
                "📊 СТАТИСТИКА\n"
                ".stats - Статистика бота",
                connection_id
            )
            return
        
        # .ping
        if text.lower() == '.ping':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(
                chat_id,
                f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}",
                connection_id
            )
            return
        
        # .time
        if text.lower() == '.time':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(
                chat_id,
                f"🕐 МСК: {get_msk_time()}",
                connection_id
            )
            return
        
        # .info
        if text.lower() == '.info':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(
                chat_id,
                f"👤 ИНФОРМАЦИЯ\n\n"
                f"🆔 ID: {user_id}\n"
                f"👤 Username: @{message.from_user.username or 'Нет'}\n"
                f"📛 Имя: {message.from_user.full_name}\n"
                f"🕐 Время: {get_msk_time()}",
                connection_id
            )
            return
        
        # .stats
        if text.lower() == '.stats':
            await delete_business_message(chat_id, message_id, connection_id)
            try:
                with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                users = set(l.get('user_id') for l in logs)
                probes = len([l for l in logs if l.get('type') == 'probe'])
                await send_to_business_chat(
                    chat_id,
                    f"📊 СТАТИСТИКА\n\n"
                    f"👤 Пользователей: {len(users)}\n"
                    f"📝 Всего команд: {len(logs)}\n"
                    f"🔍 Пробивов: {probes}\n"
                    f"🕐 Время: {get_msk_time()}",
                    connection_id
                )
            except:
                await send_to_business_chat(
                    chat_id,
                    "📊 Статистика временно недоступна",
                    connection_id
                )
            return
        
        # .whois
        if text.lower().startswith('.whois'):
            await delete_business_message(chat_id, message_id, connection_id)
            
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                await send_to_business_chat(
                    chat_id,
                    "❌ .whois ip [IP] или .whois number [НОМЕР]\n"
                    "Пример: .whois ip 8.8.8.8",
                    connection_id
                )
                return
            
            command_type = parts[1].lower()
            target = parts[2]
            
            if command_type == "ip":
                await probe_ip_business(chat_id, target, connection_id, user_id, message)
            elif command_type == "number":
                await probe_phone_business(chat_id, target, connection_id, user_id, message)
            else:
                await send_to_business_chat(
                    chat_id,
                    "❌ .whois ip [IP] или .whois number [НОМЕР]",
                    connection_id
                )
            return
        
    except Exception as e:
        logger.error(f"❌ Ошибка бизнес-сообщения: {e}")

# ========== ПРОБИВ IP В БИЗНЕС-ЧАТЕ ==========
async def probe_ip_business(chat_id, ip, connection_id, user_id, message):
    try:
        ipaddress.ip_address(ip)
    except:
        await send_to_business_chat(chat_id, f"❌ Некорректный IP: {ip}", connection_id)
        return
    
    save_log({
        "command": f".whois ip {ip}",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "target": ip,
        "time": get_msk_time()
    })
    
    loading = await show_animation(chat_id, connection_id)
    
    results, success_count = await probe_ip(ip)
    final = analyze_ip_results(results)
    
    # ФИНАЛ
    await edit_business_message(
        chat_id,
        loading.message_id,
        f"✅ РЕЗУЛЬТАТ ПРОБИВА\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 IP: {ip}\n"
        f"🌍 СТРАНА: {final['country']}\n"
        f"🏙️ РЕГИОН: {final['region']}\n"
        f"🏙️ ГОРОД: {final['city']}\n"
        f"📡 ПРОВАЙДЕР: {final['isp']}\n"
        f"🏢 ОРГАНИЗАЦИЯ: {final['org']}\n"
        f"🔗 AS: {final['as']}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final['timezone']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ОБРАБОТАНО: {success_count}/5 серверов",
        connection_id
    )

# ========== ПРОБИВ НОМЕРА В БИЗНЕС-ЧАТЕ ==========
async def probe_phone_business(chat_id, phone, connection_id, user_id, message):
    save_log({
        "command": f".whois number {phone}",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "target": phone,
        "time": get_msk_time()
    })
    
    loading = await show_animation(chat_id, connection_id)
    
    results, success_count, local_data = await probe_phone(phone)
    
    if local_data and "error" in local_data:
        await edit_business_message(chat_id, loading.message_id, f"❌ {local_data['error']}", connection_id)
        return
    
    final = analyze_phone_results(results, local_data)
    
    await edit_business_message(
        chat_id,
        loading.message_id,
        f"✅ РЕЗУЛЬТАТ ПРОБИВА\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 НОМЕР: {final['formatted']}\n"
        f"📱 НАЦИОНАЛЬНЫЙ: {final['national']}\n"
        f"📡 ОПЕРАТОР: {final['operator']}\n"
        f"🌍 РЕГИОН: {final['region']}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final['timezone']}\n"
        f"📊 ТИП: {final['type']}\n"
        f"🌐 КОД СТРАНЫ: {final['country_code']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ОБРАБОТАНО: {success_count} серверов",
        connection_id
    )

# ========== ОБЫЧНЫЕ КОМАНДЫ В ЛИЧКЕ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        await message.answer(f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ!\n📌 Причина: {get_blacklist_reason(user_id)}")
        return
    
    save_log({
        "command": "/start",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "time": get_msk_time()
    })
    
    await message.answer(
        "🔥 ДОБРО ПОЖАЛОВАТЬ В СИСТЕМУ!\n\n"
        "💡 /help - список команд\n"
        "📌 В чатах с собеседниками используй .команды (с точкой)",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        await message.answer(f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ!\n📌 Причина: {get_blacklist_reason(user_id)}")
        return
    
    await message.answer(
        "📚 СПИСОК КОМАНД\n\n"
        "🔹 В ЛИЧКЕ БОТА (с /):\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/ping - Проверка бота\n"
        "/time - Текущее время\n"
        "/info - Информация о себе\n"
        "/stats - Статистика\n\n"
        "🔹 В ЧАТАХ С СОБЕСЕДНИКАМИ (с .):\n"
        ".help - Справка\n"
        ".ping - Проверка\n"
        ".time - Время\n"
        ".info - Информация\n"
        ".stats - Статистика\n"
        ".whois ip [IP] - Пробив IP\n"
        ".whois number [НОМЕР] - Пробив номера\n\n"
        "⚡ АДМИН (только в личке):\n"
        "/block [ID] [причина]\n"
        "/unblock [ID]\n"
        "/blacklist"
    )

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")

@dp.message(Command("time"))
async def time_command(message: types.Message):
    await message.answer(f"🕐 МСК: {get_msk_time()}")

@dp.message(Command("info"))
async def info_command(message: types.Message):
    user = message.from_user
    await message.answer(
        f"👤 ИНФОРМАЦИЯ\n\n"
        f"🆔 ID: {user.id}\n"
        f"👤 Username: @{user.username or 'Нет'}\n"
        f"📛 Имя: {user.full_name}\n"
        f"🕐 Время: {get_msk_time()}"
    )

@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    try:
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        users = set(l.get('user_id') for l in logs)
        probes = len([l for l in logs if l.get('type') == 'probe'])
        await message.answer(
            f"📊 СТАТИСТИКА\n\n"
            f"👤 Пользователей: {len(users)}\n"
            f"📝 Всего команд: {len(logs)}\n"
            f"🔍 Пробивов: {probes}\n"
            f"🕐 Время: {get_msk_time()}"
        )
    except:
        await message.answer("📊 Статистика временно недоступна")

@dp.message(Command("whois"))
async def whois_command(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        await message.answer(f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ!\n📌 Причина: {get_blacklist_reason(user_id)}")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ /whois ip [IP] или /whois number [НОМЕР]")
        return
    
    command_type = args[1].lower()
    target = args[2]
    
    if command_type == "ip":
        await probe_ip_command(message, target)
    elif command_type == "number":
        await probe_phone_command(message, target)
    else:
        await message.answer("❌ Используйте: ip или number")

async def probe_ip_command(message: types.Message, ip: str):
    try:
        ipaddress.ip_address(ip)
    except:
        await message.answer(f"❌ Некорректный IP: {ip}")
        return
    
    save_log({
        "command": f"/whois ip {ip}",
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "target": ip,
        "time": get_msk_time()
    })
    
    loading = await show_animation(message)
    
    results, success_count = await probe_ip(ip)
    final = analyze_ip_results(results)
    
    await edit_normal_message(
        message.chat.id,
        loading.message_id,
        f"✅ РЕЗУЛЬТАТ ПРОБИВА\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 IP: {ip}\n"
        f"🌍 СТРАНА: {final['country']}\n"
        f"🏙️ РЕГИОН: {final['region']}\n"
        f"🏙️ ГОРОД: {final['city']}\n"
        f"📡 ПРОВАЙДЕР: {final['isp']}\n"
        f"🏢 ОРГАНИЗАЦИЯ: {final['org']}\n"
        f"🔗 AS: {final['as']}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final['timezone']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ОБРАБОТАНО: {success_count}/5 серверов"
    )

async def probe_phone_command(message: types.Message, phone: str):
    save_log({
        "command": f"/whois number {phone}",
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "target": phone,
        "time": get_msk_time()
    })
    
    loading = await show_animation(message)
    
    results, success_count, local_data = await probe_phone(phone)
    
    if local_data and "error" in local_data:
        await edit_normal_message(message.chat.id, loading.message_id, f"❌ {local_data['error']}")
        return
    
    final = analyze_phone_results(results, local_data)
    
    await edit_normal_message(
        message.chat.id,
        loading.message_id,
        f"✅ РЕЗУЛЬТАТ ПРОБИВА\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 НОМЕР: {final['formatted']}\n"
        f"📱 НАЦИОНАЛЬНЫЙ: {final['national']}\n"
        f"📡 ОПЕРАТОР: {final['operator']}\n"
        f"🌍 РЕГИОН: {final['region']}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final['timezone']}\n"
        f"📊 ТИП: {final['type']}\n"
        f"🌐 КОД СТРАНЫ: {final['country_code']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ОБРАБОТАНО: {success_count} серверов"
    )

# ========== АДМИН-КОМАНДЫ ==========
@dp.message(Command("block"))
async def block_user(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ /block [ID] [причина]\nПример: /block 123456789 Спам")
        return
    
    target_id = args[1]
    reason = args[2]
    
    if add_to_blacklist(target_id, reason, user_id):
        await message.answer(f"✅ Пользователь {target_id} добавлен в черный список!\n📌 Причина: {reason}")
    else:
        await message.answer("❌ Ошибка при добавлении в черный список")

@dp.message(Command("unblock"))
async def unblock_user(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ /unblock [ID]\nПример: /unblock 123456789")
        return
    
    target_id = args[1]
    
    if remove_from_blacklist(target_id):
        await message.answer(f"✅ Пользователь {target_id} удален из черного списка!")
    else:
        await message.answer(f"❌ Пользователь {target_id} не найден в черном списке")

@dp.message(Command("blacklist"))
async def show_blacklist(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет прав!")
        return
    
    blacklist = load_blacklist()
    if not blacklist:
        await message.answer("📭 Черный список пуст")
        return
    
    text = "⛔ ЧЕРНЫЙ СПИСОК:\n\n"
    for uid, data in blacklist.items():
        text += f"🆔 {uid}\n📌 {data.get('reason', 'Без причины')}\n👤 Добавил: {data.get('added_by', 'Неизвестно')}\n🕐 {data.get('added_at', 'Неизвестно')}\n━━━━━━━━━━━━━━\n"
    
    await message.answer(text)

# ========== КНОПКИ ==========
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if is_blacklisted(user_id):
        await callback.message.answer(f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ!\n📌 Причина: {get_blacklist_reason(user_id)}")
        await callback.answer()
        return
    
    data = callback.data
    
    if data == "probe_ip":
        await callback.message.answer("🌐 ВВЕДИТЕ IP\n📌 Пример: 8.8.8.8")
        await callback.answer()
    elif data == "probe_phone":
        await callback.message.answer("📱 ВВЕДИТЕ НОМЕР\n📌 Пример: 89001234567")
        await callback.answer()
    elif data == "stats":
        await stats_command(callback.message)
        await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🔥 БОТ С BUSINESS API ЗАПУЩЕН!")
    print("📌 Команды с / — в личке бота")
    print("📌 Команды с . — в чатах с собеседниками")
    print("=" * 60)
    
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        if "Conflict" in str(e):
            print("⚠️ Конфликт! Переподключаемся...")
            await asyncio.sleep(5)
            await dp.start_polling(bot)
        else:
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
