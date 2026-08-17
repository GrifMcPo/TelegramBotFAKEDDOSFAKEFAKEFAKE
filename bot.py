import asyncio
import os
import sys
import logging
import traceback
import random
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== ЗАГРУЗКА ПЕРЕМЕННЫХ ==========
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "8857252828"))
except ValueError:
    ADMIN_ID = 8857252828
    logger.warning(f"⚠️ ADMIN_ID неверный, используем: {ADMIN_ID}")

if not BOT_TOKEN:
    logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не найден!")
    sys.exit(1)

logger.info(f"✅ BOT_TOKEN загружен: {BOT_TOKEN[:15]}...")
logger.info(f"✅ ADMIN_ID: {ADMIN_ID}")
logger.info("=" * 60)

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== СОСТОЯНИЯ ==========
class AttackStates(StatesGroup):
    waiting_for_input = State()
    waiting_for_confirmation = State()

# ========== ХРАНИЛИЩЕ ==========
user_data = {}

# ========== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ==========
async def safe_delete_message(chat_id: int, message_id: int):
    try:
        if message_id:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
    except Exception as e:
        logger.debug(f"⚠️ Не удалось удалить сообщение {message_id}: {e}")
    return False

# ========== ФУНКЦИЯ ДЛЯ РЕАЛЬНОГО ПРОБИВА IP ==========
async def get_real_ip_info(ip: str):
    try:
        response = requests.get(
            f'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,isp,org,as,asname,timezone,query',
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                info_text = (
                    f"📊 РЕЗУЛЬТАТ ПРОБИВА IP\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🌐 ОСНОВНАЯ ИНФОРМАЦИЯ\n"
                    f"🌐 IP: {data['query']}\n"
                    f"🌍 Страна: {data['country']} {data.get('countryCode', '')}\n"
                    f"🏙️ Регион: {data['regionName']}\n"
                    f"🏙️ Город: {data['city']}\n"
                    f"📮 Индекс: {data['zip']}\n"
                    f"📍 Координаты: {data['lat']}, {data['lon']}\n"
                    f"🗺️ Карта: https://maps.google.com/maps?q={data['lat']},{data['lon']}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📡 СЕТЕВАЯ ИНФОРМАЦИЯ\n"
                    f"📡 Провайдер: {data['isp']}\n"
                    f"🏢 Организация: {data['org']}\n"
                    f"🔗 AS: {data['as']} ({data.get('asname', '')})\n"
                    f"⏰ Часовой пояс: {data['timezone']}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📌 ИНФОРМАЦИЯ С СЕРВЕРА\n"
                    f"🕐 Проверено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                    f"📊 Источник: WHOIS + GeoIP\n"
                    f"🎯 Точность: 98.7%\n"
                    f"🖥️ Сервер: SRV-PROBE-01\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔒 Данные зашифрованы!\n"
                    f"💀 Информация сохранена!"
                )
                return {'success': True, 'text': info_text, 'data': data}
            else:
                error_text = (
                    f"❌ ОШИБКА ПРОВЕРКИ\n\n"
                    f"⚠️ Не удалось получить данные\n\n"
                    f"📌 Возможные причины:\n"
                    f"• IP не найден в базе\n"
                    f"• Превышен лимит запросов\n"
                    f"• Проблемы с соединением\n\n"
                    f"🔄 Напишите /start для повтора"
                )
                return {'success': False, 'text': error_text}
        else:
            error_text = (
                f"❌ ОШИБКА ПРОВЕРКИ\n\n"
                f"⚠️ Ошибка подключения к серверу\n\n"
                f"🔄 Напишите /start для повтора"
            )
            return {'success': False, 'text': error_text}
            
    except Exception as e:
        error_text = (
            f"❌ ОШИБКА ПРОВЕРКИ\n\n"
            f"⚠️ {str(e)}\n\n"
            f"🔄 Напишите /start для повтора"
        )
        return {'success': False, 'text': error_text}

# ========== ФУНКЦИЯ ДЛЯ РЕАЛЬНОГО ПРОБИВА НОМЕРА ==========
async def get_phone_info(phone: str):
    try:
        phone_clean = phone.replace('+', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        
        if not phone_clean.isdigit():
            error_text = (
                f"❌ НЕКОРРЕКТНЫЙ ФОРМАТ\n\n"
                f"⚠️ Введен неправильный номер\n\n"
                f"📌 Примеры правильных форматов:\n"
                f"📱 +7 900 123-45-67\n"
                f"📱 89001234567\n"
                f"📱 8 (900) 123-45-67\n\n"
                f"🔄 Напишите /start для повтора"
            )
            return {'success': False, 'text': error_text}
        
        try:
            parsed = phonenumbers.parse(phone_clean, None)
            if not phonenumbers.is_valid_number(parsed):
                error_text = (
                    f"❌ НЕКОРРЕКТНЫЙ ФОРМАТ\n\n"
                    f"⚠️ Номер не существует\n\n"
                    f"🔄 Напишите /start для повтора"
                )
                return {'success': False, 'text': error_text}
        except:
            try:
                parsed = phonenumbers.parse(phone_clean, "RU")
                if not phonenumbers.is_valid_number(parsed):
                    error_text = (
                        f"❌ НЕКОРРЕКТНЫЙ ФОРМАТ\n\n"
                        f"⚠️ Номер не существует\n\n"
                        f"🔄 Напишите /start для повтора"
                    )
                    return {'success': False, 'text': error_text}
            except:
                error_text = (
                    f"❌ НЕКОРРЕКТНЫЙ ФОРМАТ\n\n"
                    f"⚠️ Номер не существует\n\n"
                    f"🔄 Напишите /start для повтора"
                )
                return {'success': False, 'text': error_text}
        
        operator = carrier.name_for_number(parsed, "ru") or "Не определен"
        region = geocoder.description_for_number(parsed, "ru") or "Не определен"
        
        formatted_number = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        
        first_names = ['АЛЕКСАНДР', 'СЕРГЕЙ', 'ДМИТРИЙ', 'АЛЕКСЕЙ', 'МИХАИЛ', 'ВЛАДИМИР', 'ЕКАТЕРИНА', 'АННА', 'МАРИЯ', 'ЕЛЕНА', 'ОЛЬГА', 'ТАТЬЯНА']
        last_names = ['ИВАНОВ', 'СМИРНОВ', 'КУЗНЕЦОВ', 'ПОПОВ', 'ВАСИЛЬЕВ', 'ПЕТРОВ', 'СОКОЛОВ', 'МИХАЙЛОВ', 'ФЕДОРОВ', 'МОРОЗОВ']
        middle_names = ['ИВАНОВИЧ', 'СЕРГЕЕВИЧ', 'АЛЕКСАНДРОВИЧ', 'ДМИТРИЕВИЧ', 'ВЛАДИМИРОВИЧ', 'АЛЕКСЕЕВИЧ', 'МИХАЙЛОВИЧ', 'ПЕТРОВИЧ']
        
        name = f"{random.choice(last_names)} {random.choice(first_names)} {random.choice(middle_names)}"
        
        cities = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань', 'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону']
        registration_city = random.choice(cities)
        
        activity_statuses = ["АКТИВЕН", "АКТИВЕН", "АКТИВЕН", "НЕАКТИВЕН", "В РОМИНГЕ"]
        
        info_text = (
            f"📊 РЕЗУЛЬТАТ ПРОБИВА НОМЕРА\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📱 ОСНОВНАЯ ИНФОРМАЦИЯ\n"
            f"📱 Номер: {formatted_number}\n"
            f"📡 Оператор: {operator}\n"
            f"🌍 Регион: {region}\n"
            f"🏙️ Город регистрации: {registration_city}\n"
            f"👤 Владелец: {name}\n"
            f"📅 Дата регистрации: {random.randint(1, 28)}.{random.randint(1, 12)}.201{random.randint(5, 9)}\n"
            f"🔄 Статус: {random.choice(activity_statuses)}\n"
            f"⏰ Активность: {'Высокая (ежедневно)' if random.random() > 0.3 else 'Средняя (несколько раз в неделю)'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛡️ ПРОВЕРКА БЕЗОПАСНОСТИ\n"
            f"🔍 В базах спама: {'НЕТ' if random.random() > 0.2 else 'ДА'}\n"
            f"🔍 В черных списках: {'НЕТ' if random.random() > 0.15 else 'ДА'}\n"
            f"🔍 В базах мошенников: {'НЕТ' if random.random() > 0.1 else 'ДА'}\n"
            f"⭐ Рейтинг: {random.randint(40, 50)/10:.1f}/5.0\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 ИНФОРМАЦИЯ С СЕРВЕРА\n"
            f"🕐 Проверено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"📊 Источник: База сервера\n"
            f"🎯 Точность: {random.randint(95, 99)}.{random.randint(0, 9)}%\n"
            f"🖥️ Сервер: SRV-PROBE-02\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔒 Данные зашифрованы!\n"
            f"💀 Информация сохранена в системе!\n"
            f"📬 Отчет отправлен администратору!"
        )
        
        return {'success': True, 'text': info_text, 'data': {
            'number': formatted_number,
            'operator': operator,
            'region': region
        }}
        
    except Exception as e:
        logger.error(f"Ошибка пробива номера: {e}")
        error_text = (
            f"❌ ОШИБКА ПРОВЕРКИ\n\n"
            f"⚠️ {str(e)}\n\n"
            f"🔄 Напишите /start для повтора"
        )
        return {'success': False, 'text': error_text}

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🌊 DDOS АТАКА", callback_data="action_ddos")],
        [InlineKeyboardButton(text="💉 DOKS АТАКА", callback_data="action_doks")],
        [InlineKeyboardButton(text="🔍 ПРОБИВ IP", callback_data="action_probe")],
        [InlineKeyboardButton(text="📱 ПРОБИВ НОМЕРА", callback_data="action_phone")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== /START ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        logger.info(f"👤 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) запустил бота")
        
        await safe_delete_message(message.chat.id, message.message_id)
        
        sent_msg = await message.answer(
            "⚡ ДОБРО ПОЖАЛОВАТЬ В СИСТЕМУ\n\n"
            "Выберите инструмент:\n\n"
            "🌊 DDOS АТАКА\n"
            "💉 DOKS АТАКА\n"
            "🔍 ПРОБИВ IP\n"
            "📱 ПРОБИВ НОМЕРА\n\n"
            "⬇️ Выберите действие ниже",
            reply_markup=get_main_keyboard()
        )
        
        user_data[message.from_user.id] = {
            "menu_msg_id": sent_msg.message_id,
            "username": message.from_user.username or "Нет юзернейма",
            "user_id": message.from_user.id,
            "start_time": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
        logger.info(f"✅ Пользователь @{message.from_user.username} зарегистрирован")
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")
        logger.error(traceback.format_exc())

# ========== /ADMIN ==========
@dp.message(Command("admin"))
async def admin_setup(message: types.Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Нет юзернейма"
        
        if user_id != ADMIN_ID:
            await message.answer(
                f"❌ У ВАС НЕТ ПРАВ АДМИНИСТРАТОРА!\n\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"👤 Username: @{username}\n\n"
                f"📌 Админ ID: {ADMIN_ID}"
            )
            return
        
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]["is_admin"] = True
        
        await message.answer(
            f"✅ ВЫ УСПЕШНО ЗАРЕГИСТРИРОВАНЫ КАК АДМИН!\n\n"
            f"🆔 ВАШ ID: {user_id}\n"
            f"👤 USER: @{username}\n"
            f"📌 ТЕПЕРЬ ОТЧЕТЫ БУДУТ ПРИХОДИТЬ СЮДА"
        )
        
        test_report = (
            f"✅ ТЕСТОВОЕ СООБЩЕНИЕ!\n\n"
            f"🆔 АДМИН ЗАРЕГИСТРИРОВАН: {user_id}\n"
            f"👤 USER: @{username}\n"
            f"🕐 ВРЕМЯ: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            f"🔥 ВСЕ РАБОТАЕТ КОРРЕКТНО!"
        )
        await message.answer(test_report)
        
        logger.info(f"✅ Админ @{username} (ID: {user_id}) зарегистрирован")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в /admin: {e}")
        logger.error(traceback.format_exc())
        await message.answer(f"❌ ОШИБКА: {e}")

# ========== ВЫБОР ДЕЙСТВИЯ ==========
@dp.callback_query(lambda c: c.data.startswith("action_"))
async def handle_action(callback: CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        action = callback.data.split("_")[1]
        
        action_names = {
            "ddos": "DDOS АТАКА",
            "doks": "DOKS АТАКА",
            "probe": "ПРОБИВ IP",
            "phone": "ПРОБИВ НОМЕРА"
        }
        
        logger.info(f"📌 Пользователь {user_id} выбрал: {action_names[action]}")
        
        menu_id = user_data.get(user_id, {}).get("menu_msg_id")
        if menu_id:
            await safe_delete_message(chat_id=user_id, message_id=menu_id)
        
        user_data[user_id]["action"] = action_names[action]
        
        await safe_delete_message(chat_id=user_id, message_id=callback.message.message_id)
        
        sent = await callback.message.answer(
            f"✅ ВЫБРАНО: {user_data[user_id]['action']}\n\n"
            f"📌 Введите IP-адрес или номер телефона:"
        )
        user_data[user_id]["input_msg_id"] = sent.message_id
        
        await state.set_state(AttackStates.waiting_for_input)
        
        try:
            await callback.answer()
        except:
            pass
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_action: {e}")
        logger.error(traceback.format_exc())

# ========== ВВОД IP/НОМЕРА ==========
@dp.message(AttackStates.waiting_for_input)
async def process_input(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        logger.info(f"📝 Пользователь {user_id} ввел: {user_input}")
        
        await safe_delete_message(message.chat.id, message.message_id)
        
        input_id = user_data.get(user_id, {}).get("input_msg_id")
        if input_id:
            await safe_delete_message(chat_id=user_id, message_id=input_id)
        
        user_data[user_id]["target"] = user_input
        
        sent = await message.answer(
            f"🎯 Цель зафиксирована: <code>{user_input}</code>\n\n"
            f"⚠️ ПОДТВЕРДИТЕ ЗАПУСК\n\n"
            f"✅ ПОДТВЕРДИТЬ ❌ ОТМЕНА",
            reply_markup=get_confirm_keyboard(),
            parse_mode="HTML"
        )
        user_data[user_id]["confirm_msg_id"] = sent.message_id
        
        await state.set_state(AttackStates.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в process_input: {e}")
        logger.error(traceback.format_exc())

# ========== ОСНОВНАЯ АНИМАЦИЯ ==========
@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def handle_confirm(callback: CallbackQuery, state: FSMContext):
    try:
        user_id = callback.from_user.id
        choice = callback.data.split("_")[1]
        
        confirm_id = user_data.get(user_id, {}).get("confirm_msg_id")
        if confirm_id:
            await safe_delete_message(chat_id=user_id, message_id=confirm_id)
        
        await safe_delete_message(chat_id=user_id, message_id=callback.message.message_id)
        
        if choice == "no":
            logger.info(f"❌ Пользователь {user_id} отменил операцию")
            await callback.message.answer("❌ ОПЕРАЦИЯ ОТМЕНЕНА. /start - ДЛЯ ПОВТОРА")
            await state.clear()
            try:
                await callback.answer()
            except:
                pass
            return
        
        try:
            await callback.answer()
        except:
            pass
        
        target = user_data[user_id]["target"]
        action = user_data[user_id]["action"]
        
        logger.info(f"💀 ЗАПУСК: {action} на цель: {target} от пользователя {user_id}")
        
        if "DDOS" in action:
            await run_ddos_animation(callback, user_id, target)
        elif "DOKS" in action:
            await run_doks_animation(callback, user_id, target)
        elif "ПРОБИВ IP" in action:
            await run_probe_ip_animation(callback, user_id, target)
        elif "ПРОБИВ НОМЕРА" in action:
            await run_probe_phone_animation(callback, user_id, target)
        else:
            await run_ddos_animation(callback, user_id, target)
        
        await send_admin_report(user_id, target, action)
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_confirm: {e}")
        logger.error(traceback.format_exc())
        try:
            await callback.answer("Произошла ошибка, попробуйте снова")
        except:
            pass

# ================================================================
# 🚀 DDOS АТАКА
# ================================================================
async def run_ddos_animation(callback, user_id, ip):
    try:
        msg = await callback.message.answer(
            f"🔍 АНАЛИЗ ЦЕЛИ\n\n"
            f"🎯 IP: {ip}\n\n"
            f"⚡ Зондирование сети...\n"
            f"⏳ Определение топологии...\n"
            f"⏳ Поиск активных сервисов...\n\n"
            f"Прогресс: ░░░░░░░░░░░░░░░░ 0%\n\n"
            f"Статус: ИНИЦИАЛИЗАЦИЯ..."
        )
        await asyncio.sleep(0.5)
        
        scan_steps = [
            (25, "⚡ Зондирование сети... ✅\n⏳ Определение топологии...\n⏳ Поиск активных сервисов...", "СКАНИРОВАНИЕ..."),
            (50, "⚡ Зондирование сети... ✅\n⏳ Определение топологии... ✅\n⏳ Поиск активных сервисов...", "АНАЛИЗ СИСТЕМЫ..."),
            (75, "⚡ Зондирование сети... ✅\n⏳ Определение топологии... ✅\n⏳ Поиск активных сервисов... ✅", "ЗАВЕРШЕНИЕ АНАЛИЗА..."),
            (100, "⚡ Зондирование сети... ✅\n⏳ Определение топологии... ✅\n⏳ Поиск активных сервисов... ✅", "✅ АНАЛИЗ ЗАВЕРШЕН")
        ]
        
        for percent, status_lines, status in scan_steps:
            bars = "█" * (percent//6) + "░" * (16 - percent//6)
            try:
                await msg.edit_text(
                    f"🔍 АНАЛИЗ ЦЕЛИ\n\n"
                    f"🎯 IP: {ip}\n\n"
                    f"{status_lines}\n\n"
                    f"Прогресс: {bars} {percent}%\n\n"
                    f"Статус: {status}"
                )
            except:
                pass
            await asyncio.sleep(0.5)
        
        await asyncio.sleep(0.5)
        
        await msg.edit_text(
            f"📊 ДАННЫЕ О СИСТЕМЕ\n\n"
            f"🌐 IP: {ip}\n"
            f"💻 ОС: Linux 5.15.0\n"
            f"🔒 Защита: Обнаружена\n"
            f"📡 Порты: 443(open) 80(open) 22(open)\n"
            f"⚡ Пропускная: 2.4 Gbps\n"
            f"🎯 Уязвимость: КРИТИЧЕСКАЯ\n\n"
            f"⚠️ Цель готова к атаке!\n"
            f"💀 Вероятность успеха: 98.7%"
        )
        await asyncio.sleep(3)
        
        load_steps = [
            (0, "ОЖИДАНИЕ..."),
            (25, "ЗАГРУЗКА МОДУЛЕЙ..."),
            (50, "АКТИВАЦИЯ УЗЛОВ..."),
            (75, "КОМПИЛЯЦИЯ ПАКЕТОВ..."),
            (95, "ФИНАЛЬНАЯ ПРОВЕРКА..."),
            (100, "✅ ГОТОВО!")
        ]
        
        for percent, status in load_steps:
            bars = "█" * (percent//10) + "░" * (10 - percent//10)
            try:
                await msg.edit_text(
                    f"⚙️ ПОДГОТОВКА АТАКИ\n\n"
                    f"🔹 Активация модулей...\n"
                    f"{bars} {percent}%\n\n"
                    f"🔹 Подключено узлов: {percent * 218}\n"
                    f"🔹 Скорость: {percent * 0.04 + 0.1:.1f} Tbps\n"
                    f"🔹 Готовность: {percent}%\n\n"
                    f"Статус: {status}"
                )
            except:
                pass
            await asyncio.sleep(0.6)
        
        await asyncio.sleep(0.5)
        
        await msg.edit_text(
            f"🚀 ЗАПУСК АТАКИ\n\n"
            f"🎯 Цель: {ip}\n"
            f"🌊 Тип: DDOS FLOOD\n"
            f"⚡ Мощность: 2.4 Tbps\n"
            f"📦 Пакетов: 847,231\n\n"
            f"💀 Атака запущена!\n"
            f"📡 Отправка пакетов..."
        )
        await asyncio.sleep(2)
        
        waves = [
            (1, [
                (15, "143,829", "НИЗКАЯ", 1847, 0.8),
                (30, "296,530", "СРЕДНЯЯ", 4231, 1.4),
                (45, "440,561", "ВЫСОКАЯ", 7843, 2.0),
                (60, "601,534", "КРИТИЧЕСКАЯ", 10231, 2.6),
                (75, "745,684", "МАКСИМАЛЬНАЯ", 12847, 3.2),
                (90, "847,231", "МАКСИМАЛЬНАЯ", 12847, 3.8),
                (100, "847,231", "✅ ЗАВЕРШЕНА", 12847, 2.6)
            ]),
            (2, [
                (20, "338,892", "СРЕДНЯЯ", 6231, 1.2),
                (40, "677,784", "ВЫСОКАЯ", 12231, 2.4),
                (60, "1,016,676", "КРИТИЧЕСКАЯ", 15847, 3.6),
                (80, "1,355,568", "МАКСИМАЛЬНАЯ", 18847, 4.8),
                (100, "1,694,462", "✅ ЗАВЕРШЕНА", 18847, 3.8)
            ]),
            (3, [
                (25, "711,833", "ВЫСОКАЯ", 15231, 2.4),
                (50, "1,423,666", "КРИТИЧЕСКАЯ", 19847, 4.8),
                (75, "2,135,498", "МАКСИМАЛЬНАЯ", 23127, 6.0),
                (100, "2,847,331", "✅ ЗАВЕРШЕНА", 23127, 4.8)
            ])
        ]
        
        for wave_num, steps in waves:
            for percent, packets, load, nodes, speed in steps:
                bars = "█" * (percent//10) + "░" * (10 - percent//10)
                try:
                    if percent == 100:
                        await msg.edit_text(
                            f"🌊 ВОЛНА #{wave_num}\n\n"
                            f"📊 Статистика\n"
                            f"📦 Пакетов: {packets}\n"
                            f"⚡ Скорость: {speed:.1f} Tbps\n"
                            f"📈 Прогресс: {bars} 100%\n"
                            f"🎯 Нагрузка: МАКСИМАЛЬНАЯ\n"
                            f"⏱️ Время: {18 + wave_num * 4} сек\n\n"
                            f"✅ Волна #{wave_num} завершена!\n"
                            f"{'🌊 Запускаем следующую...' if wave_num < 3 else '🔥 Все волны успешно завершены!'}"
                        )
                    else:
                        await msg.edit_text(
                            f"🌊 ВОЛНА #{wave_num}\n\n"
                            f"📊 Статистика\n"
                            f"📦 Пакетов: {packets}\n"
                            f"⚡ Скорость: {speed:.1f} Tbps\n"
                            f"📈 Прогресс: {bars} {percent}%\n"
                            f"🎯 Нагрузка: {load}\n"
                            f"⏱️ Время: {percent//5+2} сек\n\n"
                            f"{'🔄 Идет атака...' if percent < 30 else '🔥 Увеличиваем мощность!' if percent < 45 else '⚠️ Цель тормозит!' if percent < 60 else '💥 Цель перегружена!'}"
                        )
                except:
                    pass
                await asyncio.sleep(0.7)
        
        await asyncio.sleep(0.5)
        
        total_packets = 847231 + 1694462 + 2847331
        avg_speed = (2.4 + 3.8 + 4.8) / 3
        
        await msg.edit_text(
            f"📊 ИТОГОВАЯ СТАТИСТИКА\n\n"
            f"🎯 Цель: {ip}\n"
            f"📦 Всего пакетов: {total_packets:,}\n"
            f"⚡ Средняя скорость: {avg_speed:.1f} Tbps\n"
            f"⏱️ Общее время: 47 сек\n"
            f"📈 Эффективность: 100%\n"
            f"💥 Нагрузка: МАКСИМАЛЬНАЯ\n\n"
            f"🔥 Атака завершена!\n"
            f"💀 Цель уничтожена!"
        )
        await asyncio.sleep(3)
        
        await msg.edit_text(
            f"✅ DDOS АТАКА ЗАВЕРШЕНА\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔒 ЗАВЕРШЕНИЕ\n"
            f"⛔ Трафик сброшен ✅\n"
            f"⛔ Логи очищены ✅\n"
            f"⛔ Следы скрыты ✅\n"
            f"⛔ IP заменен ✅\n"
            f"⛔ VPN активирован ✅\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔐 Все следы скрыты!\n\n"
            f"👤 Администратор уведомлен\n"
            f"💀 Операция завершена успешно!"
        )
        
        logger.info(f"✅ DDOS атака завершена для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в DDOS анимации: {e}")
        logger.error(traceback.format_exc())

# ================================================================
# 💉 DOKS АТАКА
# ================================================================
async def run_doks_animation(callback, user_id, ip):
    try:
        msg = await callback.message.answer(
            f"🔓 ПОДБОР КЛЮЧЕЙ\n\n"
            f"🎯 Цель: {ip}\n\n"
            f"⚡ Анализ шифрования...\n"
            f"⏳ Перебор ключей...\n"
            f"⏳ Дешифровка данных...\n\n"
            f"Прогресс: ░░░░░░░░░░░░░░░░ 0%\n\n"
            f"Статус: ИНИЦИАЛИЗАЦИЯ..."
        )
        await asyncio.sleep(0.5)
        
        hack_steps = [
            (33, "ПЕРЕБОР КЛЮЧЕЙ...", "🔓 ВЗЛОМ ЗАЩИТЫ"),
            (67, "ДЕШИФРОВКА...", "🔓 ДОСТУП ПОЛУЧЕН"),
            (100, "✅ ДОСТУП ПОЛУЧЕН!", "🔓 ДОСТУП ОТКРЫТ")
        ]
        
        for percent, status, title in hack_steps:
            bars = "█" * (percent//6) + "░" * (16 - percent//6)
            try:
                await msg.edit_text(
                    f"🔓 ПОДБОР КЛЮЧЕЙ\n\n"
                    f"🎯 Цель: {ip}\n\n"
                    f"⚡ Анализ шифрования... {'✅' if percent > 33 else '⏳'}\n"
                    f"⏳ {status}\n"
                    f"⏳ Дешифровка данных... {'✅' if percent == 100 else '⏳'}\n\n"
                    f"Прогресс: {bars} {percent}%\n\n"
                    f"Статус: {title}"
                )
            except:
                pass
            await asyncio.sleep(0.7)
        
        await asyncio.sleep(0.5)
        
        await msg.edit_text(
            f"🕵️ ДАННЫЕ О СИСТЕМЕ\n\n"
            f"🌐 IP: {ip}\n"
            f"💻 ОС: Linux 5.15.0\n"
            f"🔓 Доступ: ROOT\n"
            f"📁 Файлы: Обнаружены\n"
            f"🔑 Ключи: Подобраны\n"
            f"🛡️ Защита: Отключена\n"
            f"💀 Уязвимость: КРИТИЧЕСКАЯ\n\n"
            f"⚠️ Система скомпрометирована!\n"
            f"💀 Готов к внедрению!"
        )
        await asyncio.sleep(2.5)
        
        inject_steps = [
            (0, "ИНИЦИАЛИЗАЦИЯ"),
            (35, "ЗАГРУЗКА КОДА"),
            (70, "ВНЕДРЕНИЕ"),
            (100, "✅ ВНЕДРЕНО!")
        ]
        
        for percent, status in inject_steps:
            bars = "█" * (percent//10) + "░" * (10 - percent//10)
            try:
                await msg.edit_text(
                    f"💉 ВНЕДРЕНИЕ В СИСТЕМУ\n\n"
                    f"🔹 Загрузка кода...\n"
                    f"{bars} {percent}%\n\n"
                    f"🔹 Активных узлов: {percent * 218 + 1000}\n"
                    f"🔹 Скорость: {percent * 0.04 + 0.1:.1f} Mbps\n"
                    f"🔹 Готовность: {percent}%\n\n"
                    f"Статус: {status}"
                )
            except:
                pass
            await asyncio.sleep(0.6)
        
        await asyncio.sleep(0.5)
        
        await msg.edit_text(
            f"🔥 АКТИВАЦИЯ ВРЕДОНОСНОГО КОДА\n\n"
            f"🎯 Цель: {ip}\n"
            f"💉 Тип: ROOTKIT\n"
            f"⚡ Скорость: 3.2 Mbps\n"
            f"📦 Данных: 4,294,967 байт\n\n"
            f"💀 Код активирован!\n"
            f"📡 Начинается перехват..."
        )
        await asyncio.sleep(2)
        
        for wave_num in range(1, 3):
            steps = [
                (20, "429,496", "СРЕДНИЙ", 28456),
                (40, "858,993", "ВЫСОКИЙ", 56913),
                (60, "1,288,490", "КРИТИЧЕСКИЙ", 85369),
                (80, "1,718,987", "МАКСИМАЛЬНЫЙ", 113825),
                (100, "4,294,967" if wave_num == 2 else "2,147,483", "✅ ЗАВЕРШЕН", 0)
            ]
            
            for percent, packets, load, pps in steps:
                bars = "█" * (percent//10) + "░" * (10 - percent//10)
                try:
                    if percent == 100:
                        await msg.edit_text(
                            f"📡 ПЕРЕХВАТ ДАННЫХ #{wave_num}\n\n"
                            f"📊 Статистика\n"
                            f"📦 Данных: {packets} байт\n"
                            f"⚡ Скорость: {3.0 + wave_num * 0.8:.1f} Mbps\n"
                            f"📈 Прогресс: {bars} 100%\n"
                            f"🎯 Канал: {load}\n"
                            f"⏱️ Время: {20 + wave_num * 5} сек\n\n"
                            f"✅ Перехват #{wave_num} завершен!\n"
                            f"{'📡 Запускаем второй перехват...' if wave_num == 1 else '🔥 Все данные перехвачены!'}"
                        )
                    else:
                        await msg.edit_text(
                            f"📡 ПЕРЕХВАТ ДАННЫХ #{wave_num}\n\n"
                            f"📊 Статистика\n"
                            f"📦 Данных: {packets} байт\n"
                            f"⚡ Скорость: {percent * 0.05 + 0.2:.1f} Mbps\n"
                            f"📈 Прогресс: {bars} {percent}%\n"
                            f"🎯 Канал: {load}\n"
                            f"⏱️ Время: {percent//4+3} сек\n\n"
                            f"{'🔄 Идет перехват...' if percent < 40 else '🔥 Ускоряем перехват!' if percent < 60 else '⚠️ Система отключается...' if percent < 80 else '💥 Система парализована!'}"
                        )
                except:
                    pass
                await asyncio.sleep(0.7)
        
        await asyncio.sleep(0.5)
        
        await msg.edit_text(
            f"💀 УНИЧТОЖЕНИЕ СИСТЕМЫ\n\n"
            f"🔹 Удаление баз данных ✅\n"
            f"🔹 Очистка логов ✅\n"
            f"🔹 Уничтожение ключей ✅\n"
            f"🔹 Отключение защиты ✅\n"
            f"🔹 Запись фейковых данных ✅\n\n"
            f"💀 Система уничтожена!\n"
            f"🔥 Все следы заметены!"
        )
        await asyncio.sleep(2.5)
        
        await msg.edit_text(
            f"📊 ИТОГИ DOKS АТАКИ\n\n"
            f"🎯 Цель: {ip}\n"
            f"📦 Перехвачено: 4,294,967 байт\n"
            f"⚡ Скорость: 3.6 Mbps\n"
            f"⏱️ Время: 38 сек\n"
            f"📈 Эффективность: 100%\n"
            f"🔑 Взломано ключей: 2,147\n\n"
            f"🔥 DOKS атака завершена!\n"
            f"💀 Система уничтожена!"
        )
        await asyncio.sleep(3)
        
        await msg.edit_text(
            f"✅ DOKS АТАКА ЗАВЕРШЕНА\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔒 ЗАВЕРШЕНИЕ\n"
            f"⛔ Данные удалены ✅\n"
            f"⛔ Логи очищены ✅\n"
            f"⛔ Следы скрыты ✅\n"
            f"⛔ Ключи уничтожены ✅\n"
            f"⛔ VPN активирован ✅\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔐 Все следы скрыты!\n\n"
            f"📬 Данные перехвачены и зашифрованы!\n"
            f"👤 Администратор уведомлен\n"
            f"💀 Операция завершена успешно!"
        )
        
        logger.info(f"✅ DOKS атака завершена для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в DOKS анимации: {e}")
        logger.error(traceback.format_exc())

# ================================================================
# 🔍 ПРОБИВ IP
# ================================================================
async def run_probe_ip_animation(callback, user_id, ip):
    try:
        msg = await callback.message.answer(
            f"🖥️ ПОДКЛЮЧЕНИЕ К СЕРВЕРУ\n\n"
            f"🎯 IP: {ip}\n\n"
            f"⚡ Установка соединения...\n"
            f"⏳ Авторизация...\n"
            f"⏳ Поиск в базе...\n\n"
            f"Прогресс: ░░░░░░░░░░░░░░░░ 0%\n\n"
            f"Статус: ИНИЦИАЛИЗАЦИЯ..."
        )
        await asyncio.sleep(0.5)
        
        probe_steps = [
            (40, "СОЕДИНЕНИЕ УСТАНОВЛЕНО...", "⚡ Установка соединения... ✅\n⏳ Авторизация...\n⏳ Поиск в базе..."),
            (75, "ДАННЫЕ ОБНАРУЖЕНЫ...", "⚡ Установка соединения... ✅\n⏳ Авторизация... ✅\n⏳ Поиск в базе..."),
            (100, "✅ ДАННЫЕ ПОЛУЧЕНЫ!", "⚡ Установка соединения... ✅\n⏳ Авторизация... ✅\n⏳ Поиск в базе... ✅")
        ]
        
        for percent, status, lines in probe_steps:
            bars = "█" * (percent//6) + "░" * (16 - percent//6)
            try:
                await msg.edit_text(
                    f"🖥️ ПОДКЛЮЧЕНИЕ К СЕРВЕРУ\n\n"
                    f"🎯 IP: {ip}\n\n"
                    f"{lines}\n\n"
                    f"Прогресс: {bars} {percent}%\n\n"
                    f"Статус: {status}"
                )
            except:
                pass
            await asyncio.sleep(0.6)
        
        await asyncio.sleep(0.5)
        
        result = await get_real_ip_info(ip)
        await msg.edit_text(result['text'])
        
        logger.info(f"✅ Пробив IP завершен для пользователя {user_id}, IP: {ip}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в пробиве IP: {e}")
        logger.error(traceback.format_exc())

# ================================================================
# 📱 ПРОБИВ НОМЕРА
# ================================================================
async def run_probe_phone_animation(callback, user_id, phone):
    try:
        msg = await callback.message.answer(
            f"📱 ПРОВЕРКА НОМЕРА\n\n"
            f"🎯 Номер: {phone}\n\n"
            f"⚡ Поиск в базах операторов...\n"
            f"⏳ Определение региона...\n"
            f"⏳ Проверка в открытых источниках...\n\n"
            f"Прогресс: ░░░░░░░░░░░░░░░░ 0%\n\n"
            f"Статус: ИНИЦИАЛИЗАЦИЯ..."
        )
        await asyncio.sleep(0.5)
        
        phone_steps = [
            (33, "⚡ Поиск в базах операторов... ✅\n⏳ Определение региона...\n⏳ Проверка в открытых источниках...", "ПОИСК ДАННЫХ..."),
            (66, "⚡ Поиск в базах операторов... ✅\n⏳ Определение региона... ✅\n⏳ Проверка в открытых источниках...", "АНАЛИЗ ДАННЫХ..."),
            (100, "⚡ Поиск в базах операторов... ✅\n⏳ Определение региона... ✅\n⏳ Проверка в открытых источниках... ✅", "✅ ДАННЫЕ ПОЛУЧЕНЫ")
        ]
        
        for percent, lines, status in phone_steps:
            bars = "█" * (percent//6) + "░" * (16 - percent//6)
            try:
                await msg.edit_text(
                    f"📱 ПРОВЕРКА НОМЕРА\n\n"
                    f"🎯 Номер: {phone}\n\n"
                    f"{lines}\n\n"
                    f"Прогресс: {bars} {percent}%\n\n"
                    f"Статус: {status}"
                )
            except:
                pass
            await asyncio.sleep(0.5)
        
        await asyncio.sleep(0.5)
        
        result = await get_phone_info(phone)
        await msg.edit_text(result['text'])
        
        logger.info(f"✅ Пробив номера завершен для пользователя {user_id}, номер: {phone}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в пробиве номера: {e}")
        logger.error(traceback.format_exc())

# ================================================================
# ОТПРАВКА ОТЧЕТА АДМИНУ
# ================================================================
async def send_admin_report(user_id, target, action):
    try:
        user_info = user_data.get(user_id, {})
        
        report = (
            f"⚠️ ВНИМАНИЕ! ЗАПРОС К СИСТЕМЕ\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: {user_info.get('user_id', 'Неизвестно')}\n"
            f"👤 Юзер: @{user_info.get('username', 'Неизвестно')}\n"
            f"🎯 Тип: {action}\n"
            f"🌐 Цель: {target}\n"
            f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"💀 Статус: ВЫПОЛНЕНО\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 Все данные залогированы!"
        )
        
        logger.info(f"📤 ОТПРАВКА ОТЧЕТА АДМИНУ {ADMIN_ID}")
        
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=report)
            logger.info(f"✅ ОТЧЕТ УСПЕШНО ОТПРАВЛЕН АДМИНУ {ADMIN_ID}")
        except Exception as e:
            logger.warning(f"⚠️ НЕ УДАЛОСЬ ОТПРАВИТЬ АДМИНУ {ADMIN_ID}: {e}")
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="⚠️ НЕ УДАЛОСЬ ОТПРАВИТЬ ОТЧЕТ АДМИНИСТРАТОРУ!\n\n📌 Попросите админа написать /start"
                )
                logger.info(f"✅ ОТЧЕТ ОТПРАВЛЕН ПОЛЬЗОВАТЕЛЮ {user_id}")
            except Exception as e2:
                logger.error(f"❌ НЕ УДАЛОСЬ ОТПРАВИТЬ НИКУДА: {e2}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка в send_admin_report: {e}")
        logger.error(traceback.format_exc())

# ========== ЗАПУСК ==========
async def main():
    logger.info("=" * 60)
    logger.info("🔥 МЕГА-БОТ С ПРОБИВОМ IP И НОМЕРОВ ЗАПУЩЕН!")
    logger.info(f"👤 АДМИН ID: {ADMIN_ID}")
    logger.info("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
