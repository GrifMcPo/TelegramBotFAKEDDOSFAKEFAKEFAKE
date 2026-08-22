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

# ========== ЛОГИ (ИСПРАВЛЕННЫЕ) ==========
def save_log(log_entry):
    """Сохраняет запись в лог-файл"""
    try:
        # Убеждаемся, что папка существует
        os.makedirs(os.path.dirname(LOGS_FILE) if os.path.dirname(LOGS_FILE) else '.', exist_ok=True)
        
        # Загружаем существующие логи
        logs = []
        if os.path.exists(LOGS_FILE):
            try:
                with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except:
                logs = []
        
        # Добавляем новую запись
        logs.append(log_entry)
        
        # Сохраняем
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Лог сохранен: {log_entry.get('command', 'unknown')}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения лога: {e}")
        return False

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

# ========== ПРОБИВ НОМЕРА ==========
async def probe_phone(phone: str):
    results = []
    success_count = 0
    local_data = None
    
    phone_clean = phone.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    
    try:
        parsed = phonenumbers.parse(phone_clean, None)
        
        if not phonenumbers.is_valid_number(parsed):
            return [], 0, {"error": "❌ Номер не существует или введен неверно"}
        
        operator = carrier.name_for_number(parsed, "ru") or "Не определен"
        region = geocoder.description_for_number(parsed, "ru") or "Не определен"
        timezone_info = timezone.time_zones_for_number(parsed)
        phone_type = phonenumbers.number_type(parsed)
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        country_code = parsed.country_code
        
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
        
        local_data = {
            "formatted": formatted,
            "national": national,
            "operator": operator,
            "region": region,
            "timezone": ', '.join(timezone_info) if timezone_info else "Не определен",
            "type": type_names.get(phone_type, "Неизвестный"),
            "country_code": f"+{country_code}",
            "valid": True
        }
        results.append(local_data)
        success_count += 1
        
    except phonenumbers.NumberParseException:
        return [], 0, {"error": "❌ Некорректный формат номера\nПример: 89001234567 или +79001234567"}
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга номера: {e}")
        return [], 0, {"error": f"❌ Ошибка: {str(e)}"}
    
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
        "country_code": "Не определено"
    }
    
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
    logger.info(f"🔔 ПОЛУЧЕНО БИЗНЕС-ПОДКЛЮЧЕНИЕ: {connection}")
    
    if connection.user:
        user_id = connection.user.id
        connection_id = connection.id
        username = connection.user.username or "Нет юзернейма"
        
        logger.info(f"👤 USER: {user_id}, USERNAME: @{username}, CONNECTION_ID: {connection_id}")
        
        # СОХРАНЯЕМ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ!
        business_connections[str(user_id)] = connection_id
        logger.info(f"✅ СОХРАНЕНО В business_connections: {business_connections}")
        
        logger.info(f"🔗 BUSINESS CONNECTION УСПЕШНО: @{username} (ID: {user_id})")
        
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
        
        logger.info(f"📩 ПОЛУЧЕНО СООБЩЕНИЕ В БИЗНЕС-ЧАТЕ от {user_id}: {message.text}")
        logger.info(f"🔗 connection_id: {connection_id}")
        logger.info(f"📋 business_connections: {business_connections}")
        
        # ===== СОХРАНЯЕМ CONNECTION_ID ЕСЛИ ЕЩЕ НЕТ =====
        if str(user_id) not in business_connections and connection_id:
            business_connections[str(user_id)] = connection_id
            logger.info(f"✅ СОХРАНЕН connection_id для {user_id}")
        
        # ===== ПРОВЕРЯЕМ НЕ В БАНЕ ЛИ =====
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
        
        # ===== ЕСЛИ НЕ КОМАНДА - ИГНОР =====
        if not text.startswith('.'):
            return
        
        logger.info(f"✅ ПОЛУЧЕНА КОМАНДА: {text} от {user_id}")
        
        # ===== ВСЕ КОМАНДЫ РАБОТАЮТ ДЛЯ ВСЕХ =====
        # .ban - ТОЛЬКО ДЛЯ АДМИНА
        if text.lower().startswith('.ban'):
            logger.info(f"🔨 ОБРАБОТКА .ban")
            
            if not is_admin(user_id):
                await send_to_business_chat(chat_id, "❌ У вас нет прав на бан!", connection_id)
                return
            
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
        
        # .unban - ТОЛЬКО ДЛЯ АДМИНА
        if text.lower().startswith('.unban'):
            logger.info(f"🔓 ОБРАБОТКА .unban")
            
            if not is_admin(user_id):
                await send_to_business_chat(chat_id, "❌ У вас нет прав на разбан!", connection_id)
                return
            
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
        
        # .help - ДЛЯ ВСЕХ
        if text.lower() == '.help':
            logger.info(f"📚 ОБРАБОТКА .help")
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
        
        # .ping - ДЛЯ ВСЕХ
        if text.lower() == '.ping':
            logger.info(f"🏓 ОБРАБОТКА .ping")
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(chat_id, f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}", connection_id)
            return
        
        # .time - ДЛЯ ВСЕХ
        if text.lower() == '.time':
            logger.info(f"🕐 ОБРАБОТКА .time")
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_business_chat(chat_id, f"🕐 МСК: {get_msk_time()}", connection_id)
            return
        
        # .info - ДЛЯ ВСЕХ
        if text.lower() == '.info':
            logger.info(f"👤 ОБРАБОТКА .info")
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
        
        # .stats - ДЛЯ ВСЕХ
        if text.lower() == '.stats':
            logger.info(f"📊 ОБРАБОТКА .stats")
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
        
        # .whois - ДЛЯ ВСЕХ
        if text.lower().startswith('.whois'):
            logger.info(f"🔍 ОБРАБОТКА .whois")
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
        
        logger.info(f"⏭️ НЕИЗВЕСТНАЯ КОМАНДА: {text}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка бизнес-сообщения: {e}")
        import traceback
        traceback.print_exc()

# ========== ПРОБИВ В БИЗНЕС-ЧАТЕ ==========
async def probe_ip_business(chat_id, ip, connection_id, user_id, message):
    try:
        ipaddress.ip_address(ip)
    except:
        await send_to_business_chat(chat_id, f"❌ Некорректный IP: {ip}", connection_id)
        return
    
    # СОХРАНЯЕМ ЛОГ
    save_log({
        "command": f".whois ip {ip}",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name or "Нет",
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
    # СОХРАНЯЕМ ЛОГ
    save_log({
        "command": f".whois number {phone}",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name or "Нет",
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
        if str(user_id) not in blocked_notified:
            reason = get_blacklist_reason(user_id)
            await message.answer(f"⛔ ВАС ЗАБЛОКИРОВАЛИ В БОТЕ!\n\n📌 Причина: {reason}")
            blocked_notified[str(user_id)] = True
        return
    
    save_log({
        "command": "/start",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name or "Нет",
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
        "full_name": message.from_user.full_name or "Нет",
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
        "full_name": message.from_user.full_name or "Нет",
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
    print("📌 Команды с . — в чатах с собеседниками")
    print("=" * 60)
    
    # Создаем файлы если их нет
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print(f"✅ Создан файл логов: {LOGS_FILE}")
    
    if not os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        print(f"✅ Создан файл черного списка: {BLACKLIST_FILE}")
    
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
