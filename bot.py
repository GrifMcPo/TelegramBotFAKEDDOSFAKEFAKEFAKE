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
REPO = "GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE"
BRANCH = "main"

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

def save_blacklist_to_github():
    try:
        if not GITHUB_TOKEN:
            return False
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        url = f"https://api.github.com/repos/{REPO}/contents/{BLACKLIST_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        existing = requests.get(url, headers=headers)
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {"message": f"📊 Update blacklist {get_msk_time()}", "content": encoded, "branch": BRANCH}
        if sha:
            payload["sha"] = sha
        response = requests.put(url, headers=headers, json=payload)
        return response.status_code in [200, 201]
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
    asyncio.create_task(async_save_blacklist())
    return True

def remove_from_blacklist(user_id):
    blacklist = load_blacklist()
    if str(user_id) in blacklist:
        del blacklist[str(user_id)]
        save_blacklist_local(blacklist)
        asyncio.create_task(async_save_blacklist())
        return True
    return False

def is_blacklisted(user_id):
    blacklist = load_blacklist()
    return str(user_id) in blacklist

def get_blacklist_reason(user_id):
    blacklist = load_blacklist()
    return blacklist.get(str(user_id), {}).get("reason", "Не указана")

async def async_save_blacklist():
    await asyncio.to_thread(save_blacklist_to_github)

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

def save_to_github():
    try:
        if not GITHUB_TOKEN:
            return False
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        url = f"https://api.github.com/repos/{REPO}/contents/{LOGS_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        existing = requests.get(url, headers=headers)
        sha = existing.json().get("sha") if existing.status_code == 200 else None
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {"message": f"📊 Update logs {get_msk_time()}", "content": encoded, "branch": BRANCH}
        if sha:
            payload["sha"] = sha
        response = requests.put(url, headers=headers, json=payload)
        return response.status_code in [200, 201]
    except:
        return False

def save_log(log_entry):
    save_log_local(log_entry)
    asyncio.create_task(async_save_to_github())

async def async_save_to_github():
    await asyncio.to_thread(save_to_github)

# ========== КЛАВИАТУРА ==========
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🌐 ПРОБИВ IP", callback_data="probe_ip")],
        [InlineKeyboardButton(text="📱 ПРОБИВ НОМЕРА", callback_data="probe_phone")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== АНИМАЦИЯ ==========
async def show_animation(message: types.Message):
    msg = await message.answer(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ████░░░░░░ 40%\n"
        "📡 Сервер #2... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #3... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #4... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.3)
    await msg.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ████████░░ 80%\n"
        "📡 Сервер #2... ██████░░░░ 60%\n"
        "📡 Сервер #3... ████░░░░░░ 40%\n"
        "📡 Сервер #4... ██░░░░░░░░ 20%\n"
        "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.3)
    await msg.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ██████████ 100% ✅\n"
        "📡 Сервер #2... ██████████ 100% ✅\n"
        "📡 Сервер #3... ████████░░ 80%\n"
        "📡 Сервер #4... ██████░░░░ 60%\n"
        "📡 Сервер #5... ████░░░░░░ 40%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.3)
    await msg.edit_text(
        "✅ ПОДКЛЮЧЕНИЕ ВЫПОЛНЕНО\n\n"
        "📊 Получение данных...\n"
        "⏳ Обработка информации..."
    )
    await asyncio.sleep(0.3)
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

# ========== ВСЕ КОМАНДЫ БОТА ==========

# КОМАНДА /start
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
        "💡 /help - список команд",
        reply_markup=get_main_keyboard()
    )

# КОМАНДА /help
@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        await message.answer(f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ!\n📌 Причина: {get_blacklist_reason(user_id)}")
        return
    
    save_log({
        "command": "/help",
        "user_id": user_id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "time": get_msk_time()
    })
    
    await message.answer(
        "📚 СПИСОК КОМАНД\n\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        "🔍 ПРОБИВ\n"
        "/whois ip [IP] - Пробив по IP\n"
        "/whois number [НОМЕР] - Пробив по номеру\n\n"
        "⚡ АДМИН\n"
        "/block [ID] [причина] - Добавить в ЧС\n"
        "/unblock [ID] - Удалить из ЧС\n"
        "/blacklist - Показать ЧС\n\n"
        "💡 Примеры:\n"
        "/whois ip 8.8.8.8\n"
        "/whois number 89001234567"
    )

# КОМАНДА /whois
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
    
    await loading.edit_text(
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
        await loading.edit_text(f"❌ {local_data['error']}")
        return
    
    final = analyze_phone_results(results, local_data)
    
    await loading.edit_text(
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

# КОМАНДА /stats
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    user_id = message.from_user.id
    
    if is_blacklisted(user_id):
        await message.answer(f"⛔ ВЫ В ЧЕРНОМ СПИСКЕ!\n📌 Причина: {get_blacklist_reason(user_id)}")
        return
    
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

# ========== КОМАНДЫ АДМИНА (ЧЕРНЫЙ СПИСОК) ==========

# /block - добавить в ЧС
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

# /unblock - удалить из ЧС
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

# /blacklist - показать ЧС
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
    print("🔥 БОТ ЗАПУЩЕН!")
    print("📌 Команды: /start, /help, /whois, /stats")
    print("📌 Админ: /block, /unblock, /blacklist")
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
        print("⏹️ Сохраняем логи...")
        save_to_github()
        save_blacklist_to_github()
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
