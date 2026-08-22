import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ОШИБКА: Заполните .env файл или Secrets в GitHub!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КНОПКА ДЛЯ /start ==========
def get_main_keyboard():
    buttons = [[InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== КОМАНДА /start ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🔥 БОТ ЗАПУЩЕН!\n\n"
        "Управление через сайт активировано.",
        reply_markup=get_main_keyboard()
    )

# ========== ЦИКЛ ЧТЕНИЯ САЙТА (Supabase Worker) ==========
async def fetch_commands(session):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Accept": "application/json"}
    params = {"select": "*", "order": "created_at.asc"}
    
    try:
        async with session.get(f"{SUPABASE_URL}/rest/v1/commands", headers=headers, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"❌ [Worker] Network error: {e}")
    return []

async def insert_response(session, cmd_id, result):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    payload = {"response_id": cmd_id, "result": str(result), "time": "Работает"} # Временная заглушка времени
    try:
        async with session.post(f"{SUPABASE_URL}/rest/v1/responses", headers=headers, json=payload) as resp:
            pass
    except Exception as e:
        print(f"❌ [Worker] Insert error: {e}")

async def supabase_worker():
    print("✅ Сайт-бот синхронизация: ВКЛЮЧЕНО")
    async with aiohttp.ClientSession() as session:
        while True:
            commands = await fetch_commands(session)
            
            for cmd in commands:
                cmd_id = cmd.get('id')
                text = cmd.get('command', '').strip()
                
                if text and cmd_id:
                    print(f"💻 Выполняю команду от сайта: {text}")
                    
                    # ТУТ БУДЕТ ЛОГИКА ПРОБИВА ПОЗЖЕ
                    # Сейчас просто эхо ответа
                    result = f"[SITE CMD] Вы ввели: {text}"
                    
                    await insert_response(session, cmd_id, result)
                    print(f"✅ Ответ записан в responses для ID: {cmd_id}")
            
            await asyncio.sleep(3)

# ========== ЗАПУСК ==========
async def main():
    worker_task = asyncio.create_task(supabase_worker())
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    await asyncio.gather(worker_task, polling_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен вручную")
