import aiosqlite
from datetime import datetime, timedelta
import os

DB_PATH = "logs.db"

async def init_db():
    """Создаёт таблицу при первом запуске"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
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
        await db.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON logs (user_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_time ON logs (time)')
        await db.commit()
    print("✅ База данных инициализирована")

async def save_log(log_entry):
    """Сохраняет запись в базу"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO logs (type, command, user_id, username, full_name, target, time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_entry.get('type', 'command'),
                log_entry.get('command', ''),
                log_entry.get('user_id', 0),
                log_entry.get('username', ''),
                log_entry.get('full_name', ''),
                log_entry.get('target', ''),
                log_entry.get('time', '')
            ))
            await db.commit()
            return True
    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")
        return False

async def get_all_logs(limit=200):
    """Получает последние записи"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM logs ORDER BY id DESC LIMIT ?', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Ошибка чтения БД: {e}")
        return []

async def get_users_stats():
    """Статистика по пользователям"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT user_id, username, full_name, COUNT(*) as count, MAX(time) as last
                FROM logs 
                GROUP BY user_id 
                ORDER BY count DESC
            ''')
            rows = await cursor.fetchall()
            return [dict(zip(['user_id', 'username', 'full_name', 'count', 'last'], row)) for row in rows]
    except Exception as e:
        print(f"❌ Ошибка статистики: {e}")
        return []

async def get_total_stats():
    """Общая статистика"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM logs')
            total = (await cursor.fetchone())[0]
            
            cursor = await db.execute('SELECT COUNT(DISTINCT user_id) FROM logs')
            users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM logs WHERE type = 'probe'")
            probes = (await cursor.fetchone())[0]
            
            return {'total': total, 'users': users, 'probes': probes}
    except Exception as e:
        print(f"❌ Ошибка статистики: {e}")
        return {'total': 0, 'users': 0, 'probes': 0}

async def get_user_logs(user_id):
    """Все логи конкретного пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC', (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

async def export_to_json():
    """Экспортирует логи в JSON для сайта"""
    import json
    logs = await get_all_logs(500)
    with open('logs.json', 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print("✅ JSON экспортирован")
