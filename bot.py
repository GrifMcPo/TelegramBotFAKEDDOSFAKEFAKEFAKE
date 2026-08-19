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
from aiogram import F

# ========== ЗАТКИВАЕМ ЛОГИ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

for name in logging.root.manager.loggerDict:
    if 'aiogram' in name:
        logging.getLogger(name).setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ Токен не найден!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== GITHUB API ==========
REPO_OWNER = "GrifMcPo"
REPO_NAME = "TelegramBotFAKEDDOSFAKEFAKEFAKE"
BRANCH = "main"
FILES = {
    "users": "users.json",
    "stats": "stats.json"
}

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
            logger.info(f"📄 Файл {filename} не найден")
            return None, None
        else:
            logger.error(f"❌ Ошибка получения {filename}: {response.status_code}")
            return None, None
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return None, None

def save_file_to_github(filename, data, message):
    try:
        if not GITHUB_TOKEN:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}'
        headers = get_github_headers()
        existing, sha = get_file_from_github(filename)
        content = json.dumps(data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        payload = {'message': message, 'content': encoded, 'branch': BRANCH}
        if sha:
            payload['sha'] = sha
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            logger.info(f"✅ Файл {filename} сохранен")
            return True
        else:
            logger.error(f"❌ Ошибка сохранения {filename}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False

def load_data():
    users_data = {}
    stats_data = {"total_commands": 0, "total_connections": 0, "users": {}}
    if GITHUB_TOKEN:
        logger.info("📥 Загрузка данных из GitHub...")
        users, _ = get_file_from_github(FILES["users"])
        if users:
            users_data = users
            logger.info(f"✅ Загружено {len(users_data)} пользователей")
        stats, _ = get_file_from_github(FILES["stats"])
        if stats:
            stats_data = stats
            logger.info(f"✅ Загружена статистика: {stats_data.get('total_commands', 0)} команд")
    return users_data, stats_data

def save_data(users_data, stats_data, message="📊 Update"):
    with open(FILES["users"], 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)
    with open(FILES["stats"], 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)
    if GITHUB_TOKEN:
        save_file_to_github(FILES["users"], users_data, f"📊 Update users - {get_msk_time()}")
        save_file_to_github(FILES["stats"], stats_data, f"📊 Update stats - {get_msk_time()}")

users_data, stats_data = load_data()

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
                return {'success': True, 'text': (
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
                )}
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
            parsed = phonenumbers.parse(phone_clean, "RU")
            if not phonenumbers.is_valid_number(parsed):
                return {'success': False, 'text': "❌ Номер не существует"}
        except:
            return {'success': False, 'text': "❌ Некорректный номер"}
        operator = carrier.name_for_number(parsed, "ru") or "Не определен"
        region = geocoder.description_for_number(parsed, "ru") or "Не определен"
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return {'success': True, 'text': (
            f"✅ ИНФОРМАЦИЯ О НОМЕРЕ\n\n"
            f"📱 Номер: {formatted}\n"
            f"📡 Оператор: {operator}\n"
            f"🌍 Регион: {region}\n"
            f"🏙️ Город регистрации: {region.split()[0] if region else 'Не определен'}"
        )}
    except Exception as e:
        return {'success': False, 'text': f"❌ Ошибка: {str(e)}"}

async def delete_business_message(chat_id: int, message_id: int, connection_id: str):
    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/deleteBusinessMessages'
        payload = {"business_connection_id": connection_id, "message_ids": [message_id]}
        response = requests.post(url, json=payload, timeout=10)
        if response.json().get('ok'):
            return True
        return False
    except:
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
# ОСНОВНОЙ ОБРАБОТЧИК BUSINESS MESSAGE (ВОТ ЭТОТ РАБОТАЕТ!)
# =====================================================================
@dp.business_message()
async def handle_business_message(message: types.Message):
    try:
        logger.info(f"📩 {message.from_user.username}: {message.text}")

        user_id = message.from_user.id
        chat_id = message.chat.id
        connection_id = message.business_connection_id

        if str(user_id) not in users_data:
            logger.info(f"⛔ ИГНОР: {message.from_user.username} (нет в users.json)")
            return

        if not message.text:
            return

        text = message.text
        message_id = message.message_id

        # ============================================================
        # .inf
        # ============================================================
        if text.lower() == '.inf':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(chat_id, 
                "📚 Справка\n\n"
                "🐢 ПРОБИВ\n"
                ".whois ip [IP]\n"
                ".whois number [НОМЕР]\n\n"
                "🔥 СПАМ\n"
                ".spam [N] [ТЕКСТ]\n"
                ".spams\n\n"
                "⚡ ДРУГОЕ\n"
                ".ping\n"
                ".inf",
                connection_id
            )
            return

        # ============================================================
        # .ping
        # ============================================================
        if text.lower() == '.ping':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(chat_id, f"🏓 Pong! {datetime.now().strftime('%H:%M:%S')}", connection_id)
            return

        # ============================================================
        # .whois
        # ============================================================
        if text.lower().startswith('.whois'):
            parts = text.split()
            if len(parts) < 3:
                await send_to_chat(chat_id, "❌ .whois ip [IP] или .whois number [НОМЕР]", connection_id)
                return
            
            command_type = parts[1].lower()
            target = ' '.join(parts[2:])
            
            if command_type == 'ip':
                if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', target):
                    await send_to_chat(chat_id, f"❌ Некорректный IP: {target}", connection_id)
                    return
                await delete_business_message(chat_id, message_id, connection_id)
                result = await get_ip_info(target)
                await send_to_chat(chat_id, result['text'] if result['success'] else f"❌ {result['text']}", connection_id)
                return
            
            elif command_type == 'number':
                await delete_business_message(chat_id, message_id, connection_id)
                result = await get_phone_info(target)
                await send_to_chat(chat_id, result['text'] if result['success'] else f"❌ {result['text']}", connection_id)
                return
            
            else:
                await send_to_chat(chat_id, "❌ .whois ip [IP] или .whois number [НОМЕР]", connection_id)
            return

        # ============================================================
        # .spam
        # ============================================================
        if text.lower().startswith('.spam') and not text.lower().startswith('.spams'):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                await send_to_chat(chat_id, "❌ .spam [N] [ТЕКСТ]", connection_id)
                return
            
            try:
                count = int(parts[1])
                spam_text = parts[2]
            except:
                await send_to_chat(chat_id, "❌ N должно быть числом", connection_id)
                return
            
            if count > 100:
                await send_to_chat(chat_id, "❌ Максимум 100", connection_id)
                return
            
            await delete_business_message(chat_id, message_id, connection_id)
            
            for i in range(1, count + 1):
                await send_to_chat(chat_id, f"{i}. {spam_text}", connection_id)
                await asyncio.sleep(0.3)
            
            await send_to_chat(chat_id, f"✅ Спам завершен! {count} сообщений.", connection_id)
            return

        # ============================================================
        # .spams
        # ============================================================
        if text.lower() == '.spams':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(
                chat_id,
                "🔥 Спам-меню",
                connection_id,
                reply_markup=get_spam_keyboard()
            )
            return

        # ============================================================
        # /chatid
        # ============================================================
        if text.lower() == '/chatid':
            await delete_business_message(chat_id, message_id, connection_id)
            await send_to_chat(chat_id, f"🆔 ID ЧАТА: {chat_id}", connection_id)
            return

    except Exception as e:
        logger.error(f"❌ ОШИБКА: {e}")

# =====================================================================
# BUSINESS CONNECTION
# =====================================================================
@dp.business_connection()
async def handle_business_connection(connection: types.BusinessConnection):
    if connection.user:
        user_id = connection.user.id
        username = connection.user.username or "Нет юзернейма"
        now = get_msk_time()
        
        logger.info(f"🔗 @{username} (ID: {user_id})")
        
        stats_data["total_connections"] += 1
        if str(user_id) not in stats_data["users"]:
            stats_data["users"][str(user_id)] = {"commands": 0}
        
        users_data[str(user_id)] = {
            "username": username,
            "first_name": connection.user.first_name or "Неизвестно",
            "connected_at": now,
            "last_active": now,
            "connection_id": connection.id
        }
        
        save_data(users_data, stats_data, f"🔗 New: @{username}")

# =====================================================================
# ОБЫЧНЫЕ СООБЩЕНИЯ (ЛИЧКА БОТА)
# =====================================================================
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("🤖 БОТ АКТИВЕН\n.inf - справка")

@dp.message()
async def handle_private_message(message: types.Message):
    if not message.text:
        return
    
    text = message.text
    user_id = message.from_user.id

    if text.lower() == '.inf':
        await message.answer(
            "📚 Справка\n\n"
            ".whois ip [IP]\n"
            ".whois number [НОМЕР]\n"
            ".spam [N] [ТЕКСТ]\n"
            ".spams\n"
            ".ping\n"
            ".inf"
        )
        return

    if text.lower() == '.ping':
        await message.answer(f"🏓 Pong!")
        return

    if text.lower() == '/chatid':
        await message.answer(f"🆔 {user_id}")
        return

# =====================================================================
# КНОПКИ
# =====================================================================
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    try:
        data = callback.data
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id
        connection_id = callback.business_connection_id
        
        if data == "spam_troll":
            await delete_business_message(chat_id, message_id, connection_id)
            
            await send_to_chat(chat_id, "🔥 Троллинг спам!", connection_id)
            
            for i, insult in enumerate(INSULTS, 1):
                await send_to_chat(chat_id, f"{i}. {insult}", connection_id)
                await asyncio.sleep(0.5)
            
            await send_to_chat(chat_id, "✅ Готово!", connection_id)
            await callback.answer()
            return
        
        if data in ["spam_dev", "spam_dev2"]:
            await callback.answer("⏳ В разработке!", show_alert=True)
            return
        
    except Exception as e:
        logger.error(f"❌ Ошибка в callback: {e}")

# =====================================================================
# ЗАПУСК
# =====================================================================
async def main():
    logger.info("=" * 60)
    logger.info("🔥 БОТ ЗАПУЩЕН!")
    logger.info(f"📌 Пользователей: {len(users_data)}")
    logger.info(f"📌 Команд: {stats_data.get('total_commands', 0)}")
    logger.info(f"📌 Время: {get_msk_time()} (МСК)")
    if GITHUB_TOKEN:
        logger.info("📌 GitHub API: ВКЛЮЧЕН")
    logger.info("=" * 60)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        if "Conflict" in str(e):
            logger.warning("⚠️ Конфликт, пробуем снова...")
            await asyncio.sleep(5)
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
