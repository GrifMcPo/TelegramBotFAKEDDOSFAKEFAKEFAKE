import asyncio
import os
import sys
import json
import logging
import re
import requests
import ipaddress
import phonenumbers
from phonenumbers import carrier, geocoder, timezone, number_type
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
MAIN_ADMIN = 8308522569

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

LOGS_FILE = "logs.json"
BLACKLIST_FILE = "blacklist.json"

business_connections = {}
blocked_notified = {}

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

def add_to_blacklist(user_id, reason, admin_id, time_minutes=0):
    blacklist = load_blacklist()
    expires_at = None
    if time_minutes > 0:
        expires_at = (datetime.now() + timedelta(minutes=time_minutes)).isoformat()
    
    blacklist[str(user_id)] = {
        "reason": reason,
        "added_by": admin_id,
        "added_at": get_msk_time(),
        "expires_at": expires_at
    }
    save_blacklist_local(blacklist)
    if str(user_id) in blocked_notified:
        del blocked_notified[str(user_id)]
    return True

def remove_from_blacklist(user_id):
    blacklist = load_blacklist()
    if str(user_id) in blacklist:
        del blacklist[str(user_id)]
        save_blacklist_local(blacklist)
        if str(user_id) in blocked_notified:
            del blocked_notified[str(user_id)]
        return True
    return False

def is_blacklisted(user_id):
    blacklist = load_blacklist()
    if str(user_id) not in blacklist:
        return False
    
    data = blacklist[str(user_id)]
    if data.get("expires_at"):
        expires = datetime.fromisoformat(data["expires_at"])
        if datetime.now() > expires:
            del blacklist[str(user_id)]
            save_blacklist_local(blacklist)
            if str(user_id) in blocked_notified:
                del blocked_notified[str(user_id)]
            return False
    
    return True

def get_blacklist_reason(user_id):
    blacklist = load_blacklist()
    data = blacklist.get(str(user_id), {})
    reason = data.get("reason", "Не указана")
    expires = data.get("expires_at")
    if expires:
        expires_dt = datetime.fromisoformat(expires)
        time_left = expires_dt - datetime.now()
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        if time_left.days > 0:
            time_str = f"{time_left.days}д {hours}ч"
        elif hours > 0:
            time_str = f"{hours}ч {minutes}м"
        else:
            time_str = f"{minutes}м"
        reason += f" (осталось: {time_str})"
    
    return reason

def is_admin(user_id):
    return user_id == MAIN_ADMIN

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

# ========== УДАЛЕНИЕ В БИЗНЕС-ЧАТЕ ==========
async def delete_business_message(chat_id: int, message_id: int, connection_id: str):
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteBusinessMessages'
        payload = {
            "business_connection_id": connection_id,
            "message_ids": [message_id]
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json().get('ok', False)
    except:
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
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText'
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "business_connection_id": connection_id
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json().get('ok', False)
    except:
        return False

# ========== РЕДАКТИРОВАНИЕ В ОБЫЧНОМ ЧАТЕ ==========
async def edit_normal_message(chat_id: int, message_id: int, text: str):
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text
        )
        return True
    except:
        return False

# ========== АНИМАЦИЯ ==========
async def show_animation(target, connection_id=None):
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
    
    await asyncio.sleep(0.4)
    
    if connection_id:
        await edit_business_message(target, msg.message_id,
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
    await asyncio.sleep(0.4)
    
    if connection_id:
        await edit_business_message(target, msg.message_id,
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
    await asyncio.sleep(0.4)
    
    if connection_id:
        await edit_business_message(target, msg.message_id,
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
    await asyncio.sleep(0.4)
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
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                results.append({"source": source["name"], "data": data})
        except Exception as e:
            logger.warning(f"⚠️ Ошибка {source['name']}: {e}")
            pass
    
    return results, success_count

# ========== ПРОБИВ НОМЕРА (УЛУЧШЕННЫЙ!) ==========
async def probe_phone(phone: str):
    results = []
    success_count = 0
    local_data = None
    
    phone_clean = re.sub(r'[^\d+]', '', phone)
    
    if phone_clean.startswith('8') and len(phone_clean) == 11:
        phone_clean = '+7' + phone_clean[1:]
    elif not phone_clean.startswith('+'):
        phone_clean = '+' + phone_clean
    
    try:
        parsed = phonenumbers.parse(phone_clean, "RU")
        
        if not phonenumbers.is_valid_number(parsed):
            return [], 0, {"error": "❌ Номер не существует или введен неверно"}
        
        operator = carrier.name_for_number(parsed, "ru")
        if not operator:
            national_number = str(parsed.national_number)
            country_code = parsed.country_code
            
            russian_operators = {
                '910': 'МТС', '911': 'МТС', '912': 'МТС', '913': 'МТС', '914': 'МТС',
                '915': 'МТС', '916': 'МТС', '917': 'МТС', '918': 'МТС', '919': 'МТС',
                '980': 'МТС', '981': 'МТС', '982': 'МТС', '983': 'МТС', '984': 'МТС',
                '985': 'МТС', '986': 'МТС', '987': 'МТС', '988': 'МТС', '989': 'МТС',
                '902': 'МТС', '903': 'МТС', '904': 'МТС', '905': 'МТС', '906': 'МТС',
                '908': 'МТС', '909': 'МТС', '960': 'МТС', '961': 'МТС', '962': 'МТС',
                '963': 'МТС', '964': 'МТС', '965': 'МТС', '966': 'МТС', '967': 'МТС',
                '968': 'МТС', '969': 'МТС', '990': 'МТС', '991': 'МТС', '992': 'МТС',
                '993': 'МТС', '994': 'МТС', '995': 'МТС', '996': 'МТС', '999': 'МТС',
                '920': 'Мегафон', '921': 'Мегафон', '922': 'Мегафон', '923': 'Мегафон',
                '924': 'Мегафон', '925': 'Мегафон', '926': 'Мегафон', '927': 'Мегафон',
                '928': 'Мегафон', '929': 'Мегафон', '930': 'Мегафон', '931': 'Мегафон',
                '932': 'Мегафон', '933': 'Мегафон', '934': 'Мегафон', '935': 'Мегафон',
                '936': 'Мегафон', '937': 'Мегафон', '938': 'Мегафон', '939': 'Мегафон',
                '940': 'Мегафон', '941': 'Мегафон', '942': 'Мегафон', '943': 'Мегафон',
                '944': 'Мегафон', '945': 'Мегафон', '946': 'Мегафон', '947': 'Мегафон',
                '948': 'Мегафон', '949': 'Мегафон', '950': 'Мегафон', '951': 'Мегафон',
                '952': 'Мегафон', '953': 'Мегафон', '954': 'Мегафон', '955': 'Мегафон',
                '956': 'Мегафон', '957': 'Мегафон', '958': 'Мегафон', '959': 'Мегафон',
                '900': 'Билайн', '901': 'Билайн', '902': 'Билайн', '903': 'Билайн',
                '904': 'Билайн', '905': 'Билайн', '906': 'Билайн', '907': 'Билайн',
                '908': 'Билайн', '909': 'Билайн', '950': 'Билайн', '951': 'Билайн',
                '952': 'Билайн', '953': 'Билайн', '954': 'Билайн', '955': 'Билайн',
                '956': 'Билайн', '957': 'Билайн', '958': 'Билайн', '959': 'Билайн',
                '960': 'Билайн', '961': 'Билайн', '962': 'Билайн', '963': 'Билайн',
                '964': 'Билайн', '965': 'Билайн', '966': 'Билайн', '967': 'Билайн',
                '968': 'Билайн', '969': 'Билайн', '970': 'Билайн', '971': 'Билайн',
                '972': 'Билайн', '973': 'Билайн', '974': 'Билайн', '975': 'Билайн',
                '976': 'Билайн', '977': 'Билайн', '978': 'Билайн', '979': 'Билайн',
                '980': 'Билайн', '981': 'Билайн', '982': 'Билайн', '983': 'Билайн',
                '984': 'Билайн', '985': 'Билайн', '986': 'Билайн', '987': 'Билайн',
                '988': 'Билайн', '989': 'Билайн',
                '900': 'TELE2', '901': 'TELE2', '902': 'TELE2', '903': 'TELE2',
                '904': 'TELE2', '905': 'TELE2', '906': 'TELE2', '907': 'TELE2',
                '908': 'TELE2', '909': 'TELE2', '950': 'TELE2', '951': 'TELE2',
                '952': 'TELE2', '953': 'TELE2', '954': 'TELE2', '955': 'TELE2',
                '956': 'TELE2', '957': 'TELE2', '958': 'TELE2', '959': 'TELE2',
                '960': 'TELE2', '961': 'TELE2', '962': 'TELE2', '963': 'TELE2',
                '964': 'TELE2', '965': 'TELE2', '966': 'TELE2', '967': 'TELE2',
                '968': 'TELE2', '969': 'TELE2', '970': 'TELE2', '971': 'TELE2',
                '972': 'TELE2', '973': 'TELE2', '974': 'TELE2', '975': 'TELE2',
                '976': 'TELE2', '977': 'TELE2', '978': 'TELE2', '979': 'TELE2',
                '980': 'TELE2', '981': 'TELE2', '982': 'TELE2', '983': 'TELE2',
                '984': 'TELE2', '985': 'TELE2', '986': 'TELE2', '987': 'TELE2',
                '988': 'TELE2', '989': 'TELE2'
            }
            
            if country_code == 7 and len(national_number) >= 3:
                prefix = national_number[:3]
                if prefix in russian_operators:
                    operator = russian_operators[prefix]
                elif len(national_number) >= 4:
                    prefix_4 = national_number[:4]
                    if prefix_4 in russian_operators:
                        operator = russian_operators[prefix_4]
        
        if not operator:
            operator = "Не определен"
        
        region = geocoder.description_for_number(parsed, "ru")
        if not region:
            region = "Не определен"
        
        timezone_info = timezone.time_zones_for_number(parsed)
        if not timezone_info:
            if parsed.country_code == 7:
                timezone_info = ['Europe/Moscow']
            else:
                timezone_info = ['Не определен']
        
        phone_type = phonenumbers.number_type(parsed)
        type_names = {
            0: "Неизвестный",
            1: "Стационарный",
            2: "Мобильный",
            3: "Стационарный (набор)",
            4: "VoIP",
            5: "Личный номер",
            6: "Универсальный",
            7: "Pager"
        }
        
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        
        country_codes = {
            1: 'US/CA', 7: 'RU', 44: 'GB', 49: 'DE', 33: 'FR', 39: 'IT',
            34: 'ES', 86: 'CN', 81: 'JP', 82: 'KR', 91: 'IN', 55: 'BR',
            61: 'AU', 31: 'NL', 32: 'BE', 41: 'CH', 46: 'SE', 47: 'NO',
            45: 'DK', 358: 'FI', 48: 'PL', 420: 'CZ', 36: 'HU', 40: 'RO',
            30: 'GR', 351: 'PT', 353: 'IE', 972: 'IL', 966: 'SA', 971: 'AE',
            65: 'SG', 60: 'MY', 62: 'ID', 63: 'PH', 66: 'TH', 84: 'VN'
        }
        country_name = country_codes.get(parsed.country_code, f"+{parsed.country_code}")
        
        local_data = {
            "formatted": formatted,
            "national": national,
            "operator": operator,
            "region": region,
            "timezone": ', '.join(timezone_info) if timezone_info else "Не определен",
            "type": type_names.get(phone_type, "Неизвестный"),
            "country_code": f"+{parsed.country_code}",
            "country": country_name,
            "valid": True
        }
        results.append(local_data)
        success_count += 1
        
    except phonenumbers.NumberParseException as e:
        return [], 0, {"error": f"❌ Некорректный формат номера\nПример: 89001234567 или +79001234567"}
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга номера: {e}")
        return [], 0, {"error": f"❌ Ошибка: {str(e)}"}
    
    if operator == "Не определен" or region == "Не определен":
        try:
            api_url = f"https://api.veriphone.io/v2/verify?phone={phone_clean}&default_country=RU"
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('phone_valid', False):
                    success_count += 1
                    results.append({"source": "Сервер #6 (Veriphone)", "data": data})
        except:
            pass
    
    return results, success_count, local_data

# ========== АНАЛИЗ РЕЗУЛЬТАТОВ IP ==========
def analyze_ip_results(results):
    final = {"country": "Не определено", "region": "Не определено", "city": "Не определено", 
             "isp": "Не определено", "org": "Не определено", "as": "Не определено", "timezone": "Не определено"}
    
    field_map = {
        "country": ["country", "country_name", "countryCode"],
        "region": ["region", "regionName", "region_name"],
        "city": ["city", "city_name"],
        "isp": ["isp", "org"],
        "org": ["org", "organization"],
        "as": ["as", "asn"],
        "timezone": ["timezone", "time_zone"]
    }
    
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

# ========== АНАЛИЗ РЕЗУЛЬТАТОВ НОМЕРА ==========
def analyze_phone_results(results, local_data):
    final = {
        "formatted": "Не определено",
        "national": "Не определено",
        "operator": "Не определено",
        "region": "Не определено",
        "timezone": "Не определено",
        "type": "Не определено",
        "country_code": "Не определено",
        "country": "Не определено"
    }
    
    if local_data:
        for key in final.keys():
            if key in local_data and local_data[key]:
                final[key] = local_data[key]
    
    for result in results:
        data = result.get("data", {})
        if isinstance(data, dict):
            if "carrier" in data and data["carrier"] and final["operator"] == "Не определено":
                final["operator"] = data["carrier"]
            if "location" in data and data["location"] and final["region"] == "Не определено":
                final["region"] = data["location"]
            if "country_code" in data and data["country_code"]:
                final["country_code"] = f"+{data['country_code']}"
    
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
        
        # ТОЛЬКО АДМИН МОЖЕТ ПОДКЛЮЧИТЬ БИЗНЕС-БОТА!
        if not is_admin(user_id):
            # ПРОСТО ИГНОРИРУЕМ, НИЧЕГО НЕ ОТПРАВЛЯЕМ!
            logger.info(f"🔒 Неавторизованная попытка бизнес-подключения: {user_id}")
            return
        
        business_connections[str(user_id)] = connection_id
        
        logger.info(f"🔗 BUSINESS CONNECTION: @{username} (ID: {user_id})")
        
        await bot.send_message(
            chat_id=user_id,
            text=f"✅ БОТ ПОДКЛЮЧЕН К БИЗНЕС-АККАУНТУ!\n\n"
                 f"🆔 ID: {user_id}\n"
                 f"📌 Команды работают в чатах с собеседниками!\n"
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
        
        # ТОЛЬКО АДМИН МОЖЕТ ИСПОЛЬЗОВАТЬ БИЗНЕС-БОТА!
        if not is_admin(user_id):
            # УДАЛЯЕМ СООБЩЕНИЕ И ТИХО ИГНОРИРУЕМ - НИКАКИХ УВЕДОМЛЕНИЙ!
            await delete_business_message(chat_id, message_id, connection_id)
            return
        
        if not connection_id:
            connection_id = business_connections.get(str(user_id))
        
        if is_blacklisted(user_id):
            if str(user_id) not in blocked_notified:
                reason = get_blacklist_reason(user_id)
                await delete_business_message(chat_id, message_id, connection_id)
                await send_to_business_chat(
                    chat_id,
                    f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}",
                    connection_id
                )
                blocked_notified[str(user_id)] = True
            else:
                await delete_business_message(chat_id, message_id, connection_id)
            return
        
        if not message.text:
            return
        
        text = message.text.strip()
        
        # .ban
        if text.lower().startswith('.ban'):
            await delete_business_message(chat_id, message_id, connection_id)
            
            parts = text.split(maxsplit=3)
            if len(parts) < 3:
                await send_to_business_chat(chat_id, "❌ .ban [ID] [время в минутах] [причина]", connection_id)
                return
            
            target_id = parts[1]
            try:
                time_minutes = int(parts[2])
            except:
                time_minutes = 60
            reason = parts[3] if len(parts) > 3 else "Без причины"
            
            add_to_blacklist(target_id, reason, user_id, time_minutes)
            
            await send_to_business_chat(
                chat_id,
                f"✅ {target_id} Был успешно забанен в боте!\n📌 Причина: {reason}\n⏱ Время: {time_minutes} минут",
                connection_id
            )
            
            try:
                time_str = f"{time_minutes} минут" if time_minutes > 0 else "навсегда"
                await bot.send_message(
                    chat_id=target_id,
                    text=f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}\n⏱ Время: {time_str}"
                )
            except:
                pass
            
            logger.info(f"🔨 Бан: {target_id} от {user_id} на {time_minutes} мин")
            return
        
        # .unban
        if text.lower().startswith('.unban'):
            await delete_business_message(chat_id, message_id, connection_id)
            
            parts = text.split(maxsplit=2)
            if len(parts) < 2:
                await send_to_business_chat(chat_id, "❌ .unban [ID] [причина]", connection_id)
                return
            
            target_id = parts[1]
            reason = parts[2] if len(parts) > 2 else "Без причины"
            
            if remove_from_blacklist(target_id):
                await send_to_business_chat(
                    chat_id,
                    f"✅ {target_id} был разбанен в боте!\n📌 Причина: {reason}",
                    connection_id
                )
                
                try:
                    await bot.send_message(
                        chat_id=target_id,
                        text=f"✅ ВАС РАЗБАНИЛИ В БОТЕ!\n\n📌 Причина: {reason}"
                    )
                except:
                    pass
            else:
                await send_to_business_chat(
                    chat_id,
                    f"❌ Пользователь {target_id} не найден в черном списке",
                    connection_id
                )
            return
        
        # .help
        if text.lower() == '.help':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(
                chat_id,
                "📚 СПИСОК КОМАНД\n\n"
                ".help - Справка\n"
                ".ping - Проверка\n"
                ".time - Время\n"
                ".info - Информация\n\n"
                "🔍 ПРОБИВ\n"
                ".whois ip [IP]\n"
                ".whois number [НОМЕР]\n\n"
                "📊 СТАТИСТИКА\n"
                ".stats\n\n"
                "⚡ АДМИН\n"
                ".ban [ID] [время] [причина]\n"
                ".unban [ID] [причина]",
                connection_id
            )
            return
        
        # .ping
        if text.lower() == '.ping':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(chat_id, f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}", connection_id)
            return
        
        # .time
        if text.lower() == '.time':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(chat_id, f"🕐 МСК: {get_msk_time()}", connection_id)
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
                    f"📝 Команд: {len(logs)}\n"
                    f"🔍 Пробивов: {probes}\n"
                    f"🕐 Время: {get_msk_time()}",
                    connection_id
                )
            except:
                await send_to_business_chat(chat_id, "📊 Статистика временно недоступна", connection_id)
            return
        
        # .whois
        if text.lower().startswith('.whois'):
            await delete_business_message(chat_id, message_id, connection_id)
            
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                await send_to_business_chat(
                    chat_id,
                    "❌ .whois ip [IP] или .whois number [НОМЕР]",
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

# ========== ПРОБИВ В БИЗНЕС-ЧАТЕ ==========
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
        f"🌍 СТРАНА: {final['country']}\n"
        f"📡 ОПЕРАТОР: {final['operator']}\n"
        f"🏙️ РЕГИОН: {final['region']}\n"
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
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
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
        "📌 В чатах с собеседниками используй .команды",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    
    await message.answer(
        "📚 СПИСОК КОМАНД\n\n"
        "🔹 В ЛИЧКЕ БОТА (с /):\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/ping - Проверка\n"
        "/time - Время\n"
        "/info - Информация\n"
        "/stats - Статистика\n"
        "/whois ip [IP] - Пробив IP\n"
        "/whois number [НОМЕР] - Пробив номера\n"
        "/ban [ID] [время] [причина] - Бан (админ)\n"
        "/unban [ID] [причина] - Разбан (админ)\n\n"
        "🔹 В ЧАТАХ (с .):\n"
        ".help - Справка\n"
        ".ping - Проверка\n"
        ".time - Время\n"
        ".info - Информация\n"
        ".stats - Статистика\n"
        ".whois ip [IP] - Пробив IP\n"
        ".whois number [НОМЕР] - Пробив номера\n"
        ".ban [ID] [время] [причина] - Бан (админ)\n"
        ".unban [ID] [причина] - Разбан (админ)"
    )

@dp.message(Command("ping"))
async def ping(message: types.Message):
    user_id = message.from_user.id
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    await message.answer(f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}")

@dp.message(Command("time"))
async def time_command(message: types.Message):
    user_id = message.from_user.id
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    await message.answer(f"🕐 МСК: {get_msk_time()}")

@dp.message(Command("info"))
async def info_command(message: types.Message):
    user_id = message.from_user.id
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
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
    user_id = message.from_user.id
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    try:
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        users = set(l.get('user_id') for l in logs)
        probes = len([l for l in logs if l.get('type') == 'probe'])
        await message.answer(
            f"📊 СТАТИСТИКА\n\n"
            f"👤 Пользователей: {len(users)}\n"
            f"📝 Команд: {len(logs)}\n"
            f"🔍 Пробивов: {probes}\n"
            f"🕐 Время: {get_msk_time()}"
        )
    except:
        await message.answer("📊 Статистика временно недоступна")

@dp.message(Command("whois"))
async def whois_command(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    
    args = message.text.split(maxsplit=2)
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
        await message.answer("❌ Используйте: /whois ip [IP] или /whois number [НОМЕР]")

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
        f"🌍 СТРАНА: {final['country']}\n"
        f"📡 ОПЕРАТОР: {final['operator']}\n"
        f"🏙️ РЕГИОН: {final['region']}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final['timezone']}\n"
        f"📊 ТИП: {final['type']}\n"
        f"🌐 КОД СТРАНЫ: {final['country_code']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ОБРАБОТАНО: {success_count} серверов"
    )

@dp.message(Command("ban"))
async def ban_command(message: types.Message):
    user_id = message.from_user.id    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав на бан!")
        return
    
    args = message.text.split(maxsplit=3)
    if len(args) < 3:
        await message.answer("❌ /ban [ID] [время в минутах] [причина]")
        return
    
    target_id = args[1]
    try:
        time_minutes = int(args[2])
    except:
        time_minutes = 60
    reason = args[3] if len(args) > 3 else "Без причины"
    
    add_to_blacklist(target_id, reason, user_id, time_minutes)
    
    await message.answer(f"✅ {target_id} Был успешно забанен в боте!\n📌 Причина: {reason}\n⏱ Время: {time_minutes} минут")
    
    try:
        time_str = f"{time_minutes} минут" if time_minutes > 0 else "навсегда"
        await bot.send_message(
            chat_id=target_id,
            text=f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}\n⏱ Время: {time_str}"
        )
    except:
        pass

@dp.message(Command("unban"))
async def unban_command(message: types.Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав на разбан!")
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("❌ /unban [ID] [причина]")
        return
    
    target_id = args[1]
    reason = args[2] if len(args) > 2 else "Без причины"
    
    if remove_from_blacklist(target_id):
        await message.answer(f"✅ {target_id} был разбанен в боте!\n📌 Причина: {reason}")
        
        try:
            await bot.send_message(
                chat_id=target_id,
                text=f"✅ ВАС РАЗБАНИЛИ В БОТЕ!\n\n📌 Причина: {reason}"
            )
        except:
            pass
    else:
        await message.answer(f"❌ Пользователь {target_id} не найден в черном списке")

@dp.message()
async def handle_private_message(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    
    if not message.text:
        return
    
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    if text.startswith('.'):
        await message.answer(
            "❌ Команды с . работают только в чатах с собеседниками!\n"
            "📌 В личке используй команды с / (например /help)"
        )
        return
    
    await message.answer(
        "❓ Неизвестная команда\n\n"
        "📌 Введи /help для списка команд\n"
        "📌 В чатах с собеседниками используй .команды"
    )

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if is_blacklisted(user_id):
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await callback.message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
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

async def main():
    print("=" * 60)
    print("🔥 БОТ ЗАПУЩЕН!")
    print(f"👤 АДМИН: {MAIN_ADMIN}")
    print("📌 Команды с / — в личке бота")
    print("📌 Команды с . — в чатах с собеседниками (только для админа)")
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
