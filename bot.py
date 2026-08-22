import asyncio
import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from supabase import create_client, Client

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIN_ADMIN = int(os.getenv("MAIN_ADMIN", 8308522569))

# Используем SERVICE ROLE KEY! Публичный ключ тут работать не будет.
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 

if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Ошибка: не хватает переменных окружения!")
    sys.exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

LOGS_FILE = "docs/data/logs.json"
BLACKLIST_FILE = "docs/data/blacklist.json"
blocked_notified = {}

def get_msk_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')

# ... [ВСТАВЬТЕ СЮДА ВАШ КОД ФУНКЦИЙ ЧЕРНОГО СПИСКА save_log И execute_command из прошлого сообщения] ...
# Весь код функций add_to_blacklist, remove_from_blacklist, is_blacklisted, save_log, get_logs_for_user, get_all_users, execute_command остается неизменным.

async def process_commands():
    while True:
        try:
            # Берем самую старую необработанную команду
            response = (
                supabase.table('commands')
                .select('*')
                .is_('response_id', 'null') 
                .order('id')
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                cmd = response.data[0]
                command_id = cmd['id']
                command_text = cmd['command']
                
                print(f"📥 Получена команда от сайта: {command_text} (ID: {command_id})")
                
                result = execute_command(command_text)
                
                resp_data = {
                    'result': result,
                    'time': get_msk_time(),
                    'response_id': command_id
                }
                resp_result = supabase.table('responses').insert(resp_data).execute()
                
                if resp_result.data:
                    response_id = resp_result.data[0]['id']
                    supabase.table('commands').update({'response_id': response_id}).eq('id', command_id).execute()
                    print(f"✅ Ответ записан (Resp ID: {response_id})")
            
        except Exception as e:
            print(f"❌ Error in loop: {e}")
        
        await asyncio.sleep(2)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🔥 Бот-страж запущен. Управление через веб-панель.")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("📚 Все команды выполняются только через сайт /admin.")

@dp.message()
async def handle_message(message: types.Message):
    await message.answer("❌ Прямые команды в Telegram отключены. Используйте сайт.")

async def main():
    os.makedirs('docs/data', exist_ok=True)
    for file in [LOGS_FILE, BLACKLIST_FILE]:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f:
                json.dump([] if file.endswith('.json') else {}, f)

    asyncio.create_task(process_commands())
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    asyncio.run(main())
