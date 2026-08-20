import asyncio
import os
import sys
import logging
import re
import requests
import json
import ipaddress
import phonenumbers
from phonenumbers import carrier, geocoder, timezone, number_type
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== НАСТРОЙКА ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗЫ ДЛЯ ПРОВЕРКИ IP ==========
IP_SOURCES = [
    {"name": "Сервер #1", "url": "http://ip-api.com/json/{}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query"},
    {"name": "Сервер #2", "url": "https://ipinfo.io/{}/json"},
    {"name": "Сервер #3", "url": "http://ipwhois.io/json/{}"},
    {"name": "Сервер #4", "url": "https://freegeoip.app/json/{}"},
    {"name": "Сервер #5", "url": "https://ipapi.co/{}/json"},
]

# ========== БАЗЫ ДЛЯ ПРОВЕРКИ НОМЕРА ==========
PHONE_SOURCES = [
    {"name": "Сервер #1", "type": "local"},
    {"name": "Сервер #2", "url": "https://api.numverify.com/validate?number={}&access_key=YOUR_KEY"},
    {"name": "Сервер #3", "url": "https://phonevalidation.abstractapi.com/v1/?api_key=YOUR_KEY&phone={}"},
    {"name": "Сервер #4", "url": "https://api.veriphone.io/v2/verify?phone={}&api_key=YOUR_KEY"},
    {"name": "Сервер #5", "url": "https://api.apilayer.com/number_verification/validate?number={}"},
]

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🌐 ПРОБИВ IP", callback_data="probe_ip")],
        [InlineKeyboardButton(text="📱 ПРОБИВ НОМЕРА", callback_data="probe_phone")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ФУНКЦИЯ ПРОБИВА IP ==========
async def probe_ip(ip: str):
    results = []
    success_count = 0
    
    for source in IP_SOURCES:
        try:
            url = source["url"].format(ip)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                results.append({
                    "source": source["name"],
                    "data": data
                })
        except:
            pass
    
    return results, success_count

# ========== ФУНКЦИЯ ПРОБИВА НОМЕРА ==========
async def probe_phone(phone: str):
    results = []
    success_count = 0
    local_data = None
    
    # Очищаем номер
    phone_clean = phone.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    
    # Локальная проверка через phonenumbers
    try:
        parsed = phonenumbers.parse(phone_clean, None)
        if not phonenumbers.is_valid_number(parsed):
            return [], 0, {"error": "Номер не найден в базе"}
        
        operator = carrier.name_for_number(parsed, "ru") or "Не определено"
        region = geocoder.description_for_number(parsed, "ru") or "Не определено"
        timezone_info = timezone.time_zones_for_number(parsed)
        phone_type = phonenumbers.number_type(parsed)
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        
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
            "source": "Сервер #1",
            "formatted": formatted,
            "national": national,
            "operator": operator,
            "region": region,
            "timezone": ', '.join(timezone_info) if timezone_info else "Не определено",
            "type": type_names.get(phone_type, "Неизвестный"),
            "valid": True,
            "country_code": str(parsed.country_code)
        }
        results.append(local_data)
        success_count += 1
    except:
        pass
    
    # Внешние API
    for source in PHONE_SOURCES:
        if source.get("type") == "local":
            continue
        try:
            url = source["url"].format(phone_clean)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                results.append({
                    "source": source["name"],
                    "data": data
                })
        except:
            pass
    
    return results, success_count, local_data

# ========== АНАЛИЗ ДАННЫХ IP ==========
def analyze_ip_results(results):
    final = {
        "country": "Не определено",
        "region": "Не определено",
        "city": "Не определено",
        "isp": "Не определено",
        "org": "Не определено",
        "as": "Не определено",
        "timezone": "Не определено"
    }
    
    field_map = {
        "country": ["country", "country_name", "countryCode"],
        "region": ["region", "regionName", "region_name"],
        "city": ["city", "city_name"],
        "isp": ["isp", "org"],
        "org": ["org", "organization"],
        "as": ["as", "asn"],
        "timezone": ["timezone", "time_zone"]
    }
    
    # Собираем все значения
    values = {key: [] for key in final.keys()}
    
    for result in results:
        data = result.get("data", {})
        for field, aliases in field_map.items():
            for alias in aliases:
                if alias in data and data[alias]:
                    values[field].append(data[alias])
                    break
    
    # Выбираем самое частое
    from collections import Counter
    for field, vals in values.items():
        if vals:
            counter = Counter(vals)
            final[field] = counter.most_common(1)[0][0]
    
    return final

# ========== АНАЛИЗ ДАННЫХ НОМЕРА ==========
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
    
    # Сначала берем локальные данные как основные
    if local_data:
        for key in final.keys():
            if key in local_data:
                final[key] = local_data[key]
    
    # Дополняем из внешних источников
    for result in results:
        if "data" not in result:
            continue
        data = result["data"]
        
        # Пытаемся найти оператора
        if final["operator"] == "Не определено" or final["operator"] == "Не определен":
            for key in ["carrier", "operator", "org"]:
                if key in data and data[key]:
                    final["operator"] = data[key]
                    break
        
        # Пытаемся найти регион
        if final["region"] == "Не определено" or final["region"] == "Не определен":
            for key in ["region", "location", "country"]:
                if key in data and data[key]:
                    final["region"] = data[key]
                    break
        
        # Пытаемся найти тип
        if final["type"] == "Не определено" or final["type"] == "Не определен":
            for key in ["line_type", "phone_type", "type"]:
                if key in data and data[key]:
                    final["type"] = data[key]
                    break
    
    return final

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🔥 ДОБРО ПОЖАЛОВАТЬ В СИСТЕМУ\n\n"
        "📌 Бот для получения информации по IP и номерам\n"
        "📌 Использует несколько серверов для проверки\n\n"
        "💡 Для списка команд введите /help",
        reply_markup=get_main_keyboard()
    )

# ========== КОМАНДА /HELP ==========
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📚 СПИСОК КОМАНД\n\n"
        "────────────────────\n"
        "🐢 ИНФОРМАЦИЯ\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        "────────────────────\n"
        "🔍 ПРОБИВ\n"
        "/whois ip [IP] - Пробив по IP-адресу\n"
        "/whois number [НОМЕР] - Пробив по номеру телефона\n\n"
        "────────────────────\n"
        "📊 СТАТИСТИКА\n"
        "/stats - Статистика бота\n\n"
        "────────────────────\n"
        "💡 Примеры:\n"
        "/whois ip 8.8.8.8\n"
        "/whois number 89001234567"
    )

# ========== КОМАНДА /WHOIS ==========
@dp.message(Command("whois"))
async def whois_command(message: types.Message):
    args = message.text.split()
    
    if len(args) < 3:
        await message.answer(
            "❌ Неправильный формат\n\n"
            "📌 /whois ip [IP-адрес]\n"
            "📌 /whois number [Номер телефона]\n\n"
            "💡 Примеры:\n"
            "/whois ip 8.8.8.8\n"
            "/whois number 89001234567"
        )
        return
    
    command_type = args[1].lower()
    target = args[2]
    
    if command_type == "ip":
        await probe_ip_command(message, target)
    elif command_type == "number":
        await probe_phone_command(message, target)
    else:
        await message.answer("❌ Неизвестный тип\nИспользуйте: ip или number")

# ========== ПРОБИВ IP С АНИМАЦИЕЙ ==========
async def probe_ip_command(message: types.Message, ip: str):
    try:
        ipaddress.ip_address(ip)
    except:
        await message.answer(f"❌ Некорректный IP-адрес: {ip}")
        return
    
    # АНИМАЦИЯ
    loading = await message.answer(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ████░░░░░░ 40%\n"
        "📡 Сервер #2... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #3... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #4... ░░░░░░░░░░ 0%\n"
        "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ████████░░ 80%\n"
        "📡 Сервер #2... ██████░░░░ 60%\n"
        "📡 Сервер #3... ████░░░░░░ 40%\n"
        "📡 Сервер #4... ██░░░░░░░░ 20%\n"
        "📡 Сервер #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ██████████ 100% ✅\n"
        "📡 Сервер #2... ██████████ 100% ✅\n"
        "📡 Сервер #3... ████████░░ 80%\n"
        "📡 Сервер #4... ██████░░░░ 60%\n"
        "📡 Сервер #5... ████░░░░░░ 40%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 Сервер #1... ██████████ 100% ✅\n"
        "📡 Сервер #2... ██████████ 100% ✅\n"
        "📡 Сервер #3... ██████████ 100% ✅\n"
        "📡 Сервер #4... ████████░░ 80%\n"
        "📡 Сервер #5... ██████░░░░ 60%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "✅ ПОДКЛЮЧЕНИЕ ВЫПОЛНЕНО\n\n"
        "📊 Получение данных...\n"
        "⏳ Обработка информации..."
    )
    await asyncio.sleep(0.5)
    
    # Получаем данные
    results, success_count = await probe_ip(ip)
    final = analyze_ip_results(results)
    
    response = (
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
    
    await loading.edit_text(response)

# ========== ПРОБИВ НОМЕРА С АНИМАЦИЕЙ ==========
async def probe_phone_command(message: types.Message, phone: str):
    # АНИМАЦИЯ
    loading = await message.answer(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 База операторов... ████░░░░░░ 40%\n"
        "📡 База регионов... ░░░░░░░░░░ 0%\n"
        "📡 База провайдеров... ░░░░░░░░░░ 0%\n"
        "📡 Анализ номера... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 База операторов... ████████░░ 80%\n"
        "📡 База регионов... ██████░░░░ 60%\n"
        "📡 База провайдеров... ████░░░░░░ 40%\n"
        "📡 Анализ номера... ██░░░░░░░░ 20%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ\n\n"
        "📡 База операторов... ██████████ 100% ✅\n"
        "📡 База регионов... ██████████ 100% ✅\n"
        "📡 База провайдеров... ████████░░ 80%\n"
        "📡 Анализ номера... ██████░░░░ 60%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "✅ ПОДКЛЮЧЕНИЕ ВЫПОЛНЕНО\n\n"
        "📊 Получение данных...\n"
        "⏳ Обработка информации..."
    )
    await asyncio.sleep(0.5)
    
    # Получаем данные
    results, success_count, local_data = await probe_phone(phone)
    
    if local_data and "error" in local_data:
        await loading.edit_text(f"❌ {local_data['error']}")
        return
    
    final = analyze_phone_results(results, local_data)
    
    response = (
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
    
    await loading.edit_text(response)

# ========== СТАТИСТИКА ==========
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await message.answer(
        "📊 СТАТИСТИКА\n\n"
        "👤 Пользователей: 0\n"
        "📝 Выполнено запросов: 0\n"
        "🌐 Серверов IP: 5\n"
        "📱 Серверов номеров: 5\n\n"
        "✅ Система работает стабильно"
    )

# ========== КНОПКИ ==========
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    
    if data == "probe_ip":
        await callback.message.answer(
            "🌐 ВВЕДИТЕ IP-АДРЕС\n\n"
            "📌 Пример: 8.8.8.8\n"
            "💡 Или используйте команду:\n"
            "/whois ip 8.8.8.8"
        )
        await callback.answer()
    
    elif data == "probe_phone":
        await callback.message.answer(
            "📱 ВВЕДИТЕ НОМЕР ТЕЛЕФОНА\n\n"
            "📌 Пример: 89001234567\n"
            "💡 Или используйте команду:\n"
            "/whois number 89001234567"
        )
        await callback.answer()
    
    elif data == "stats":
        await stats_command(callback.message)
        await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🔥 БОТ ЗАПУЩЕН!")
    print("📌 Команды: /start, /help, /whois ip, /whois number")
    print("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
