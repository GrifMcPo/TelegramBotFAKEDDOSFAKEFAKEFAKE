# Telegram Bot Control Room

Сайт записывает команды в Supabase, Python-worker выполняет execute_command и возвращает результат в responses. Сайт не использует Telegram API.

## Запуск

1. Выполните supabase/schema.sql в SQL Editor Supabase.
2. Скопируйте .env.example в .env и заполните BOT_TOKEN, SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY.
3. Установите зависимости: pip install -r requirements.txt
4. Запустите: python bot.py
5. В docs/script.js укажите URL Supabase и публичный anon key.

Команды: /stats, /idlist, /logs ID, /ban ID минуты причина, /unban ID, /help, /ping, /time.
