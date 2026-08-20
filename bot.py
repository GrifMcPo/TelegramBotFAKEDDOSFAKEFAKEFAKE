import asyncio
import os
import sys
import logging
import re
import requests
import json
import sqlite3
import ipaddress
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8857252828"))

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== SQLite БАЗА ДАННЫХ ==========
DB_FILE = "logs.db"

def init_db():
    """Создаёт таблицу если её нет"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            command TEXT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            target TEXT,
            time TEXT
        )
    ''')
    # Индексы для быстрого поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON logs (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_time ON logs (time)')
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

def save_log(log_entry):
    """Сохраняет запись в базу"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (type, command, user_id, username, full_name, target, time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_entry.get('type', 'command'),
            log_entry.get('command', ''),
            log_entry.get('user_id', 0),
            log_entry.get('username', ''),
            log_entry.get('full_name', ''),
            log_entry.get('target', ''),
            log_entry.get('time', get_msk_time())
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в БД: {e}")
        return False

def get_all_logs(limit=100):
    """Получает последние записи"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logs ORDER BY id DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'type': row[1],
                'command': row[2],
                'user_id': row[3],
                'username': row[4],
                'full_name': row[5],
                'target': row[6],
                'time': row[7]
            })
        return logs
    except Exception as e:
        logger.error(f"❌ Ошибка чтения БД: {e}")
        return []

def get_users_stats():
    """Статистика по пользователям"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, full_name, COUNT(*) as count, MAX(time) as last
            FROM logs 
            GROUP BY user_id 
            ORDER BY count DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'user_id': row[0],
                'username': row[1] or 'Нет',
                'full_name': row[2] or 'Нет',
                'count': row[3],
                'last': row[4] or 'Нет'
            })
        return users
    except Exception as e:
        logger.error(f"❌ Ошибка статистики: {e}")
        return []

def get_total_stats():
    """Общая статистика"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM logs')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM logs')
        users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM logs WHERE type = 'probe'")
        probes = cursor.fetchone()[0]
        
        conn.close()
        return {'total': total, 'users': users, 'probes': probes}
    except Exception as e:
        logger.error(f"❌ Ошибка статистики: {e}")
        return {'total': 0, 'users': 0, 'probes': 0}

def get_user_logs(user_id):
    """Все логи конкретного пользователя"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'type': row[1],
                'command': row[2],
                'user_id': row[3],
                'username': row[4],
                'full_name': row[5],
                'target': row[6],
                'time': row[7]
            })
        return logs
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return []

# Инициализируем БД при запуске
init_db()

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🌐 ПРОБИВ IP", callback_data="probe_ip")],
        [InlineKeyboardButton(text="📱 ПРОБИВ НОМЕРА", callback_data="probe_phone")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== АНИМАЦИЯ ПОДКЛЮЧЕНИЯ ==========
async def show_connection_animation(message: types.Message):
    msg = await message.answer(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ████░░░░░░ 40%\n"
        "📡 Сервер #2... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #3... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #4... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.6)
    
    await msg.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ████████░░ 80%\n"
        "📡 Сервер #2... ██████░░░░ 60%\n"
        "📡 Сервер #3... ████░░░░░░ 40%\n"
        "📡 Сервер #4... ██░░░░░░░░ 20%\n"
        "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.6)
    
    await msg.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ██████████ 100% ✅\n"
        "📡 Сервер #2... ██████████ 100% ✅\n"
        "📡 Сервер #3... ████████░░ 80%\n"
        "📡 Сервер #4... ██████░░░░ 60%\n"
        "📡 Сервер #5... ████░░░░░░ 40%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.6)
    
    await msg.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ██████████ 100% ✅\n"
        "📡 Сервер #2... ██████████ 100% ✅\n"
        "📡 Сервер #3... ██████████ 100% ✅\n"
        "📡 Сервер #4... ████████░░ 80%\n"
        "📡 Сервер #5... ██████░░░░ 60%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.6)
    
    await msg.edit_text(
        "✅ ПОДКЛЮЧЕНИЕ ВЫПОЛНЕНО\n\n"
        "📊 Получение данных...\n"
        "⏳ Обработка информации..."
    )
    await asyncio.sleep(0.5)
    
    return msg

# ========== ФУНКЦИЯ ПРОБИВА IP ==========
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
        except:
            pass
    
    return results, success_count

# ========== ФУНКЦИЯ ПРОБИВА НОМЕРА ==========
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
                "source": "Сервер #1",
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

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    save_log({
        "type": "command",
        "command": "/start",
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "time": get_msk_time()
    })
    
    await message.answer(
        "🔥 ДОБРО ПОЖАЛОВАТЬ В СИСТЕМУ\n\n"
        "📌 Бот для получения информации по IP и номерам\n\n"
        "💡 /help - список команд",
        reply_markup=get_main_keyboard()
    )

# ========== КОМАНДА /HELP ==========
@dp.message(Command("help"))
async def help_command(message: types.Message):
    save_log({
        "type": "command",
        "command": "/help",
        "user_id": message.from_user.id,
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
        "💡 Примеры:\n"
        "/whois ip 8.8.8.8\n"
        "/whois number 89001234567"
    )

# ========== КОМАНДА /WHOIS ==========
@dp.message(Command("whois"))
async def whois_command(message: types.Message):
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

# ========== ПРОБИВ IP ==========
async def probe_ip_command(message: types.Message, ip: str):
    try:
        ipaddress.ip_address(ip)
    except:
        await message.answer(f"❌ Некорректный IP: {ip}")
        return
    
    save_log({
        "type": "probe",
        "command": f"/whois ip {ip}",
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "target": ip,
        "time": get_msk_time()
    })
    
    loading = await show_connection_animation(message)
    
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

# ========== ПРОБИВ НОМЕРА ==========
async def probe_phone_command(message: types.Message, phone: str):
    save_log({
        "type": "probe",
        "command": f"/whois number {phone}",
        "user_id": message.from_user.id,
        "username": message.from_user.username or "Нет",
        "full_name": message.from_user.full_name,
        "target": phone,
        "time": get_msk_time()
    })
    
    loading = await show_connection_animation(message)
    
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

# ========== СТАТИСТИКА ==========
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    stats = get_total_stats()
    
    await message.answer(
        f"📊 СТАТИСТИКА\n\n"
        f"👤 Пользователей: {stats['users']}\n"
        f"📝 Всего команд: {stats['total']}\n"
        f"🔍 Пробивов: {stats['probes']}\n"
        f"🕐 Время: {get_msk_time()}"
    )

# ========== КНОПКИ ==========
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
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
    print("📌 База данных: logs.db (SQLite)")
    print("📌 Команды: /start, /help, /whois ip, /whois number")
    print("=" * 60)
    
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
