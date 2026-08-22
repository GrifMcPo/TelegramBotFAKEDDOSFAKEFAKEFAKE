import asyncio, json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MAIN_ADMIN = int(os.getenv("MAIN_ADMIN", "0"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))
if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("Ошибка: нужны BOT_TOKEN, SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
DATA_DIR = Path(os.getenv("DATA_DIR", "docs/data"))
LOGS_FILE, BLACKLIST_FILE = DATA_DIR / "logs.json", DATA_DIR / "blacklist.json"


def now_msk():
    return datetime.now(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")

def load_json(path, default):
    try:
        with path.open("r", encoding="utf-8") as f: return json.load(f)
    except (OSError, json.JSONDecodeError): return default

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f: json.dump(value, f, indent=2, ensure_ascii=False)
    temp.replace(path)

def load_blacklist():
    value = load_json(BLACKLIST_FILE, {})
    return value if isinstance(value, dict) else {}

def add_to_blacklist(user_id, reason, admin_id, time_minutes=0):
    data = load_blacklist()
    expires = (datetime.now() + timedelta(minutes=time_minutes)).isoformat() if time_minutes > 0 else None
    data[str(user_id)] = {"reason": reason, "added_by": admin_id, "added_at": now_msk(), "expires_at": expires}
    save_json(BLACKLIST_FILE, data)
    return True

def remove_from_blacklist(user_id):
    data = load_blacklist()
    if str(user_id) not in data: return False
    del data[str(user_id)]
    save_json(BLACKLIST_FILE, data)
    return True

def is_blacklisted(user_id):
    entry = load_blacklist().get(str(user_id))
    if not entry: return False
    try:
        if entry.get("expires_at") and datetime.now() > datetime.fromisoformat(entry["expires_at"]):
            remove_from_blacklist(user_id); return False
    except ValueError: pass
    return True

def save_log(entry):
    logs = load_json(LOGS_FILE, [])
    if not isinstance(logs, list): logs = []
    logs.append(entry); save_json(LOGS_FILE, logs); return True

def get_logs_for_user(identifier):
    logs, result = load_json(LOGS_FILE, []), []
    identifier = identifier.lower().lstrip("@")
    cutoff = datetime.now() - timedelta(days=5)
    for log in logs if isinstance(logs, list) else []:
        try:
            if datetime.strptime(log.get("time", ""), "%d.%m.%Y %H:%M:%S") < cutoff: continue
        except ValueError: pass
        if identifier.isdigit() and str(log.get("user_id", "")) == identifier: result.append(log)
        elif not identifier.isdigit() and identifier in str(log.get("username", "")).lower().lstrip("@"): result.append(log)
    return result

def all_users():
    return {str(x.get("user_id")) for x in load_json(LOGS_FILE, []) if x.get("user_id") is not None}

def execute_command(command):
    try:
        command = command.strip(); low = command.lower()
        if not command: return "❌ Команда не может быть пустой"
        if low == "/stats":
            logs = load_json(LOGS_FILE, []); probes = sum("whois" in str(x.get("command", "")).lower() for x in logs)
            return "📊 СТАТИСТИКА\n\n👤 Пользователей: " + str(len(all_users())) + "\n📝 Команд: " + str(len(logs)) + "\n🔍 Пробивов: " + str(probes) + "\n🕐 Время: " + now_msk()
        if low == "/idlist": return "👤 СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n\n" + ("\n".join(sorted(all_users())) or "Список пуст")
        if low.startswith("/logs "):
            ident, logs = command[6:].strip(), get_logs_for_user(command[6:].strip())
            if not logs: return "❌ Логи не найдены для " + ident
            out = ["📊 ЛОГИ ДЛЯ: " + ident, "📝 Всего команд: " + str(len(logs)), "🕐 За последние 5 дней", ""]
            for x in logs[-50:]: out += ["🕐 " + x.get("time", ""), "📝 " + x.get("command", "Неизвестно")]
            return "\n".join(out)
        if low == "/help": return "📚 КОМАНДЫ\n\n/stats — статистика\n/idlist — пользователи\n/logs ID — логи\n/ban ID минуты причина\n/unban ID причина\n/ping — проверка\n/time — время"
        if low == "/ping": return "🏓 Pong! " + datetime.now().strftime("%H:%M:%S")
        if low == "/time": return "🕐 МСК: " + now_msk()
        if low.startswith("/ban "):
            p = command.split(maxsplit=3)
            if len(p) < 3: return "❌ /ban [ID] [время в минутах] [причина]"
            try: minutes = max(0, int(p[2]))
            except ValueError: minutes = 60
            reason = p[3] if len(p) > 3 else "Без причины"
            add_to_blacklist(p[1], reason, MAIN_ADMIN, minutes)
            save_log({"command": "/ban " + p[1], "user_id": MAIN_ADMIN, "username": "WEB", "target": p[1], "reason": reason, "time": now_msk()})
            return "✅ " + p[1] + " заблокирован\n📌 Причина: " + reason + "\n⏱ Время: " + str(minutes) + " минут"
        if low.startswith("/unban "):
            p = command.split(maxsplit=2)
            if len(p) < 2: return "❌ /unban [ID] [причина]"
            if remove_from_blacklist(p[1]): return "✅ " + p[1] + " разблокирован"
            return "❌ Пользователь " + p[1] + " не найден в чёрном списке"
        return "❌ Неизвестная команда: " + command + "\nВведите /help для списка команд"
    except Exception as e: return "❌ Ошибка выполнения команды: " + str(e)

async def process_commands():
    while True:
        try:
            pending = supabase.table("commands").select("*").is_("response_id", "null").order("id").limit(1).execute()
            if pending.data:
                cmd = pending.data[0]; result = execute_command(cmd.get("command", ""))
                response = supabase.table("responses").insert({"result": result, "time": now_msk(), "response_id": cmd["id"]}).execute()
                if response.data: supabase.table("commands").update({"response_id": response.data[0]["id"]}).eq("id", cmd["id"]).execute()
                print("Обработана команда #" + str(cmd["id"]))
        except Exception as e: print("Ошибка worker: " + str(e))
        await asyncio.sleep(POLL_INTERVAL)

@dp.message(Command("start"))
async def start(message: types.Message): await message.answer("🔥 Бот запущен. Управление — через веб-панель.")
@dp.message()
async def handle_message(message: types.Message): await message.answer("❌ Прямые команды отключены. Используйте веб-панель.")

async def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LOGS_FILE.exists(): save_json(LOGS_FILE, [])
    if not BLACKLIST_FILE.exists(): save_json(BLACKLIST_FILE, {})
    await asyncio.gather(process_commands(), dp.start_polling(bot))

if __name__ == "__main__": asyncio.run(main())
