import asyncio
import os
import sys
import logging
import re
import requests
import json
import socket
import ipaddress
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
    {
        "name": "ip-api.com",
        "url": "http://ip-api.com/json/{}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query",
        "fields": ["country", "regionName", "city", "isp", "org", "as", "timezone"]
    },
    {
        "name": "ipinfo.io",
        "url": "https://ipinfo.io/{}/json",
        "fields": ["country", "region", "city", "org", "timezone", "loc"]
    },
    {
        "name": "ip-api.io",
        "url": "http://ip-api.io/json/{}",
        "fields": ["country_name", "region_name", "city", "isp", "organization"]
    },
    {
        "name": "ipgeolocation.io",
        "url": "https://api.ipgeolocation.io/ipgeo?ip={}&apiKey=YOUR_KEY",
        "fields": ["country_name", "state_prov", "city", "isp", "organization"]
    },
    {
        "name": "ipwhois.io",
        "url": "http://ipwhois.io/json/{}",
        "fields": ["country", "region", "city", "isp", "org", "timezone"]
    },
    {
        "name": "freegeoip.app",
        "url": "https://freegeoip.app/json/{}",
        "fields": ["country_name", "region_name", "city", "time_zone"]
    },
    {
        "name": "ipapi.co",
        "url": "https://ipapi.co/{}/json",
        "fields": ["country_name", "region", "city", "org", "timezone"]
    },
    {
        "name": "ipbase.com",
        "url": "https://api.ipbase.com/v2/info?ip={}&apikey=YOUR_KEY",
        "fields": ["country", "region", "city", "isp", "asn"]
    },
    {
        "name": "ipdata.co",
        "url": "https://api.ipdata.co/{}?api-key=YOUR_KEY",
        "fields": ["country_name", "region", "city", "isp", "asn"]
    },
    {
        "name": "abuseipdb.com",
        "url": "https://api.abuseipdb.com/api/v2/check?ipAddress={}",
        "fields": ["countryCode", "isp", "domain", "usageType"]
    },
    {
        "name": "virustotal.com",
        "url": "https://www.virustotal.com/api/v3/ip_addresses/{}",
        "fields": ["country", "asn", "network"]
    },
    {
        "name": "shodan.io",
        "url": "https://api.shodan.io/shodan/host/{}?key=YOUR_KEY",
        "fields": ["country_name", "region_code", "city", "org", "isp"]
    },
    {
        "name": "ip2location.com",
        "url": "https://api.ip2location.com/v2/?ip={}&key=YOUR_KEY&package=WS25",
        "fields": ["country_name", "region_name", "city_name", "isp", "as"]
    },
    {
        "name": "ipstack.com",
        "url": "https://api.ipstack.com/{}?access_key=YOUR_KEY",
        "fields": ["country_name", "region_name", "city", "isp", "organization"]
    },
    {
        "name": "ipvigilante.com",
        "url": "https://ipvigilante.com/json/{}",
        "fields": ["country_name", "region_name", "city", "isp", "organization"]
    },
    {
        "name": "ipgeolocationapi.com",
        "url": "https://ipgeolocationapi.com/api/v1/ip/{}",
        "fields": ["country_name", "region", "city", "timezone"]
    },
    {
        "name": "ip.belurk.com",
        "url": "https://ip.belurk.com/json/{}",
        "fields": ["country", "region", "city", "isp", "as"]
    },
    {
        "name": "ip-api.org",
        "url": "https://ip-api.org/json/{}",
        "fields": ["country", "region", "city", "isp", "org"]
    },
    {
        "name": "ipstack.org",
        "url": "https://ipstack.org/json/{}",
        "fields": ["country_name", "region_name", "city", "isp", "as"]
    },
    {
        "name": "ipinfo.org",
        "url": "https://ipinfo.org/json/{}",
        "fields": ["country", "region", "city", "org", "timezone"]
    }
]

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🌐 ПРОБИВ IP", callback_data="probe_ip")],
        [InlineKeyboardButton(text="📱 ПРОБИВ НОМЕРА", callback_data="probe_phone")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== ФУНКЦИЯ ПРОБИВА IP (20+ БАЗ) ==========
async def probe_ip(ip: str):
    results = []
    success_count = 0
    
    for api in IP_APIS:
        try:
            url = api["url"].format(ip)
            headers = {}
            
            # Для AbuseIPDB нужен специальный заголовок
            if "abuseipdb" in api["name"]:
                headers = {"Key": os.getenv("ABUSEIPDB_KEY", "")}
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                
                # Собираем данные из ответа
                info = {"source": api["name"]}
                for field in api["fields"]:
                    if field in data and data[field]:
                        info[field] = data[field]
                
                results.append(info)
            else:
                results.append({"source": api["name"], "error": f"Status {response.status_code}"})
        except Exception as e:
            results.append({"source": api["name"], "error": str(e)})
    
    return results, success_count

# ========== АНАЛИЗ И СРАВНЕНИЕ ДАННЫХ ==========
def analyze_results(results):
    """Сравнивает данные из всех источников и вычисляет точность"""
    fields = {
        "country": [],
        "region": [],
        "city": [],
        "isp": [],
        "org": [],
        "as": [],
        "timezone": []
    }
    
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
    
    # Вычисляем самые частые значения
    final = {}
    accuracy = {}
    
    for field, values in fields.items():
        if values:
            from collections import Counter
            counter = Counter(values)
            most_common = counter.most_common(1)[0]
            final[field] = most_common[0]
            accuracy[field] = (most_common[1] / len(values)) * 100
        else:
            final[field] = "Не определено"
            accuracy[field] = 0
    
    # Общая точность
    avg_accuracy = sum(accuracy.values()) / len(accuracy) if accuracy else 0
    
    return final, accuracy, avg_accuracy

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🔥 ДОБРО ПОЖАЛОВАТЬ В СИСТЕМУ ПРОБИВОВ\n\n"
        "📌 Бот для получения информации по IP и номерам телефонов\n"
        "📌 Использует 20+ источников данных\n\n"
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

# ========== КОМАНДА /WHOIS IP ==========
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
        await message.answer("⏳ Функция в разработке...")
    else:
        await message.answer("❌ Неизвестный тип\nИспользуйте: ip или number")

# ========== ПРОБИВ IP ==========
async def probe_ip_command(message: types.Message, ip: str):
    # Проверка IP
    try:
        ipaddress.ip_address(ip)
    except:
        await message.answer(f"❌ Некорректный IP-адрес: {ip}")
        return
    
    # Отправляем "загрузку"
    loading = await message.answer("🔍 Поиск информации об IP...\n⏳ Обработка 20+ источников...")
    
    # Получаем данные
    results, success_count = await probe_ip(ip)
    
    # Анализируем
    final, accuracy, avg_accuracy = analyze_results(results)
    
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
        f"📊 ИСТОЧНИКИ: {success_count}/20\n"
        f"🎯 ТОЧНОСТЬ: {avg_accuracy:.1f}%\n\n"
        f"🔒 Данные собраны из открытых источников"
    )
    
    # Редактируем сообщение
    await loading.edit_text(response)

# ========== СТАТИСТИКА ==========
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await message.answer(
        "📊 СТАТИСТИКА БОТА\n\n"
        "👤 Пользователей: 0\n"
        "📝 Выполнено запросов: 0\n"
        "🌐 Источников данных: 20\n"
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
    print("📌 Использует 20+ источников данных")
    print("📌 Команды: /start, /help, /whois ip")
    print("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
