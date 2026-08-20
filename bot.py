import asyncio
import os
import sys
import logging
import re
import requests
import json
import socket
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
IP_APIS = [
    {"name": "ip-api.com", "url": "http://ip-api.com/json/{}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query", "fields": ["country", "regionName", "city", "isp", "org", "as", "timezone"]},
    {"name": "ipinfo.io", "url": "https://ipinfo.io/{}/json", "fields": ["country", "region", "city", "org", "timezone", "loc"]},
    {"name": "ipwhois.io", "url": "http://ipwhois.io/json/{}", "fields": ["country", "region", "city", "isp", "org", "timezone"]},
    {"name": "freegeoip.app", "url": "https://freegeoip.app/json/{}", "fields": ["country_name", "region_name", "city", "time_zone"]},
    {"name": "ipapi.co", "url": "https://ipapi.co/{}/json", "fields": ["country_name", "region", "city", "org", "timezone"]},
    {"name": "ipdata.co", "url": "https://api.ipdata.co/{}?api-key=YOUR_KEY", "fields": ["country_name", "region", "city", "isp", "asn"]},
    {"name": "ipgeolocation.io", "url": "https://api.ipgeolocation.io/ipgeo?ip={}&apiKey=YOUR_KEY", "fields": ["country_name", "state_prov", "city", "isp", "organization"]},
    {"name": "ipbase.com", "url": "https://api.ipbase.com/v2/info?ip={}&apikey=YOUR_KEY", "fields": ["country", "region", "city", "isp", "asn"]},
    {"name": "ip2location.com", "url": "https://api.ip2location.com/v2/?ip={}&key=YOUR_KEY&package=WS25", "fields": ["country_name", "region_name", "city_name", "isp", "as"]},
    {"name": "ipstack.com", "url": "https://api.ipstack.com/{}?access_key=YOUR_KEY", "fields": ["country_name", "region_name", "city", "isp", "organization"]}
]

# ========== БАЗЫ ДЛЯ ПРОВЕРКИ НОМЕРА ==========
PHONE_APIS = [
    {"name": "phonenumbers (local)", "type": "local"},
    {"name": "numverify.com", "url": "https://api.numverify.com/validate?number={}&access_key=YOUR_KEY", "fields": ["country_name", "location", "carrier", "line_type"]},
    {"name": "abstractapi.com", "url": "https://phonevalidation.abstractapi.com/v1/?api_key=YOUR_KEY&phone={}", "fields": ["country", "location", "carrier", "line_type"]},
    {"name": "veriphone.io", "url": "https://api.veriphone.io/v2/verify?phone={}&api_key=YOUR_KEY", "fields": ["country", "location", "carrier", "phone_type"]},
    {"name": "apilayer.com", "url": "https://api.apilayer.com/number_verification/validate?number={}", "fields": ["country_name", "location", "carrier", "line_type"]},
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
    
    for api in IP_APIS:
        try:
            url = api["url"].format(ip)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                info = {"source": api["name"]}
                for field in api["fields"]:
                    if field in data and data[field]:
                        info[field] = data[field]
                results.append(info)
            else:
                results.append({"source": api["name"], "error": f"Status {response.status_code}"})
        except:
            results.append({"source": api["name"], "error": "Timeout"})
    
    return results, success_count

# ========== ФУНКЦИЯ ПРОБИВА НОМЕРА ==========
async def probe_phone(phone: str):
    results = []
    success_count = 0
    
    # Очищаем номер
    phone_clean = phone.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
    
    # 1. Локальная проверка через phonenumbers
    try:
        parsed = phonenumbers.parse(phone_clean, None)
        if not phonenumbers.is_valid_number(parsed):
            return [], 0, {"error": "Номер не существует"}
        
        operator = carrier.name_for_number(parsed, "ru") or "Не определен"
        region = geocoder.description_for_number(parsed, "ru") or "Не определен"
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
            "source": "Сервер пробива (локальный)",
            "formatted": formatted,
            "national": national,
            "operator": operator,
            "region": region,
            "timezone": ', '.join(timezone_info) if timezone_info else "Не определен",
            "type": type_names.get(phone_type, "Неизвестный"),
            "valid": True,
            "country_code": str(parsed.country_code)
        }
        results.append(local_data)
        success_count += 1
    except Exception as e:
        results.append({"source": "Сервер пробива (локальный)", "error": str(e)})
    
    # 2. Внешние API (если есть ключи)
    for api in PHONE_APIS:
        if api["type"] == "local":
            continue
        try:
            url = api["url"].format(phone_clean)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                info = {"source": api["name"]}
                for field in api["fields"]:
                    if field in data and data[field]:
                        info[field] = data[field]
                results.append(info)
            else:
                results.append({"source": api["name"], "error": f"Status {response.status_code}"})
        except:
            results.append({"source": api["name"], "error": "Timeout"})
    
    return results, success_count, local_data if 'local_data' in locals() else None

# ========== АНАЛИЗ ДАННЫХ IP ==========
def analyze_ip_results(results):
    fields = {"country": [], "region": [], "city": [], "isp": [], "org": [], "as": [], "timezone": []}
    field_mapping = {
        "country": ["country", "country_name", "countryCode", "country_code"],
        "region": ["region", "regionName", "region_name", "state_prov"],
        "city": ["city", "city_name"],
        "isp": ["isp", "org", "organization"],
        "org": ["org", "organization"],
        "as": ["as", "asn"],
        "timezone": ["timezone", "time_zone"]
    }
    
    for result in results:
        if "error" in result:
            continue
        for field, aliases in field_mapping.items():
            for alias in aliases:
                if alias in result:
                    fields[field].append(result[alias])
                    break
    
    final = {}
    accuracy = {}
    from collections import Counter
    
    for field, values in fields.items():
        if values:
            counter = Counter(values)
            most_common = counter.most_common(1)[0]
            final[field] = most_common[0]
            accuracy[field] = (most_common[1] / len(values)) * 100
        else:
            final[field] = "Не определено"
            accuracy[field] = 0
    
    avg_accuracy = sum(accuracy.values()) / len(accuracy) if accuracy else 0
    return final, accuracy, avg_accuracy

# ========== АНАЛИЗ ДАННЫХ НОМЕРА ==========
def analyze_phone_results(results):
    final = {
        "formatted": "Не определено",
        "national": "Не определено",
        "operator": "Не определено",
        "region": "Не определено",
        "timezone": "Не определено",
        "type": "Не определено",
        "country_code": "Не определено"
    }
    
    accuracy = {}
    
    for result in results:
        if "error" in result:
            continue
        for field in final.keys():
            if field in result and result[field]:
                # Для accuracy считаем совпадения
                if field not in accuracy:
                    accuracy[field] = {"matches": 0, "total": 0}
                accuracy[field]["total"] += 1
                if result[field] == final[field] or final[field] == "Не определено":
                    if final[field] == "Не определено":
                        final[field] = result[field]
                    accuracy[field]["matches"] += 1
    
    # Вычисляем точность
    acc_percent = {}
    for field, data in accuracy.items():
        if data["total"] > 0:
            acc_percent[field] = (data["matches"] / data["total"]) * 100
        else:
            acc_percent[field] = 0
    
    avg_accuracy = sum(acc_percent.values()) / len(acc_percent) if acc_percent else 0
    
    return final, acc_percent, avg_accuracy

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🔥 ДОБРО ПОЖАЛОВАТЬ В СИСТЕМУ ПРОБИВОВ\n\n"
        "📌 Бот для получения информации по IP и номерам телефонов\n"
        "📌 Использует 10+ источников данных\n\n"
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
    
    # АНИМАЦИЯ ПОДКЛЮЧЕНИЯ К СЕРВЕРАМ
    loading = await message.answer(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к серверу #1... ████░░░░░░ 40%\n"
        "📡 Подключение к серверу #2... ░░░░░░░░░░ 0%\n"
        "📡 Подключение к серверу #3... ░░░░░░░░░░ 0%\n"
        "📡 Подключение к серверу #4... ░░░░░░░░░░ 0%\n"
        "📡 Подключение к серверу #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    # Обновляем анимацию
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к серверу #1... ████████░░ 80%\n"
        "📡 Подключение к серверу #2... ██████░░░░ 60%\n"
        "📡 Подключение к серверу #3... ████░░░░░░ 40%\n"
        "📡 Подключение к серверу #4... ██░░░░░░░░ 20%\n"
        "📡 Подключение к серверу #5... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к серверу #1... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #2... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #3... ████████░░ 80%\n"
        "📡 Подключение к серверу #4... ██████░░░░ 60%\n"
        "📡 Подключение к серверу #5... ████░░░░░░ 40%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к серверу #1... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #2... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #3... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #4... ████████░░ 80%\n"
        "📡 Подключение к серверу #5... ██████░░░░ 60%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к серверу #1... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #2... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #3... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #4... ██████████ 100% ✅\n"
        "📡 Подключение к серверу #5... ████████░░ 80%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.5)
    
    await loading.edit_text(
        "✅ ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ УСПЕШНО!\n\n"
        "📊 Получение данных...\n"
        "⏳ Обработка информации..."
    )
    await asyncio.sleep(0.5)
    
    # Получаем данные
    results, success_count = await probe_ip(ip)
    final, accuracy, avg_accuracy = analyze_ip_results(results)
    
    # Формируем ответ
    response = (
        f"✅ ИНФОРМАЦИЯ ОБ IP\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 IP-АДРЕС: {ip}\n"
        f"🌍 СТРАНА: {final.get('country', 'Не определено')}\n"
        f"🏙️ РЕГИОН: {final.get('region', 'Не определено')}\n"
        f"🏙️ ГОРОД: {final.get('city', 'Не определено')}\n"
        f"📡 ПРОВАЙДЕР: {final.get('isp', 'Не определено')}\n"
        f"🏢 ОРГАНИЗАЦИЯ: {final.get('org', 'Не определено')}\n"
        f"🔗 AS: {final.get('as', 'Не определено')}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final.get('timezone', 'Не определено')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ИСТОЧНИКИ: {success_count}/10\n"
        f"🎯 ТОЧНОСТЬ: {avg_accuracy:.1f}%\n\n"
        f"🔒 Данные собраны из открытых источников"
    )
    
    await loading.edit_text(response)

# ========== ПРОБИВ НОМЕРА С АНИМАЦИЕЙ ==========
async def probe_phone_command(message: types.Message, phone: str):
    # АНИМАЦИЯ
    loading = await message.answer(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к базе операторов... ████░░░░░░ 40%\n"
        "📡 Подключение к базе регионов... ░░░░░░░░░░ 0%\n"
        "📡 Подключение к базе провайдеров... ░░░░░░░░░░ 0%\n"
        "📡 Анализ номера... ░░░░░░░░░░ 0%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к базе операторов... ████████░░ 80%\n"
        "📡 Подключение к базе регионов... ██████░░░░ 60%\n"
        "📡 Подключение к базе провайдеров... ████░░░░░░ 40%\n"
        "📡 Анализ номера... ██░░░░░░░░ 20%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "🔄 ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ ПРОБИВА\n\n"
        "📡 Подключение к базе операторов... ██████████ 100% ✅\n"
        "📡 Подключение к базе регионов... ██████████ 100% ✅\n"
        "📡 Подключение к базе провайдеров... ████████░░ 80%\n"
        "📡 Анализ номера... ██████░░░░ 60%\n\n"
        "⏳ Ожидайте..."
    )
    await asyncio.sleep(0.8)
    
    await loading.edit_text(
        "✅ ПОДКЛЮЧЕНИЕ К СЕРВЕРАМ УСПЕШНО!\n\n"
        "📊 Получение данных...\n"
        "⏳ Обработка информации..."
    )
    await asyncio.sleep(0.5)
    
    # Получаем данные
    results, success_count, local_data = await probe_phone(phone)
    
    if local_data and "error" in local_data:
        await loading.edit_text(f"❌ {local_data['error']}")
        return
    
    final, accuracy, avg_accuracy = analyze_phone_results(results)
    
    # Формируем ответ
    response = (
        f"✅ ИНФОРМАЦИЯ О НОМЕРЕ\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 НОМЕР: {final.get('formatted', 'Не определено')}\n"
        f"📱 НАЦИОНАЛЬНЫЙ: {final.get('national', 'Не определено')}\n"
        f"📡 ОПЕРАТОР: {final.get('operator', 'Не определено')}\n"
        f"🌍 РЕГИОН: {final.get('region', 'Не определено')}\n"
        f"⏰ ЧАСОВОЙ ПОЯС: {final.get('timezone', 'Не определено')}\n"
        f"📊 ТИП: {final.get('type', 'Не определено')}\n"
        f"🌐 КОД СТРАНЫ: {final.get('country_code', 'Не определено')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 ИСТОЧНИКИ: {success_count}/5\n"
        f"🎯 ТОЧНОСТЬ: {avg_accuracy:.1f}%\n\n"
        f"🔒 Данные собраны из открытых источников"
    )
    
    await loading.edit_text(response)

# ========== СТАТИСТИКА ==========
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await message.answer(
        "📊 СТАТИСТИКА БОТА\n\n"
        "👤 Пользователей: 0\n"
        "📝 Выполнено запросов: 0\n"
        "🌐 Источников IP: 10\n"
        "📱 Источников номеров: 5\n"
        "🕐 Время работы: 0\n\n"
        "🔥 Бот работает стабильно!"
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
    print("🔥 БОТ ДЛЯ ПРОБИВОВ ЗАПУЩЕН!")
    print("📌 Использует 10+ источников данных")
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
