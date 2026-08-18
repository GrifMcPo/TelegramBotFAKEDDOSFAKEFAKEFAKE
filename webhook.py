import asyncio
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, types
from aiogram.types.business_messages_deleted import BusinessMessagesDeleted
from flask import Flask, request, jsonify

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8857252828"))

if not BOT_TOKEN:
    print("❌ Токен не найден!")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)

# ========== КЕШ СООБЩЕНИЙ (ВРЕМЕННЫЙ) ==========
message_cache = {}

# ========== ОБРАБОТКА БИЗНЕС-ОБНОВЛЕНИЙ ==========
@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        data = request.get_json()
        logger.info(f"📩 Получено обновление: {data}")

        # Проверяем, есть ли бизнес-обновления
        if 'update_id' in data and 'business_connection' in data:
            connection = data['business_connection']
            connection_id = connection.get('id')
            
            # Проверяем, есть ли удаленные сообщения
            if 'business_messages_deleted' in data:
                deleted_data = data['business_messages_deleted']
                chat_id = deleted_data.get('chat_id')
                message_ids = deleted_data.get('message_ids', [])
                
                logger.info(f"🗑️ УДАЛЕНЫ СООБЩЕНИЯ В ЧАТЕ {chat_id}")
                logger.info(f"📌 ID сообщений: {message_ids}")
                
                # Отправляем отчет админу
                for msg_id in message_ids:
                    # Ищем сообщение в кеше
                    cache_key = f"{chat_id}_{msg_id}"
                    if cache_key in message_cache:
                        msg_text, from_user = message_cache[cache_key]
                        
                        report = (
                            f"⚠️ ЗАФИКСИРОВАНО УДАЛЕННОЕ СООБЩЕНИЕ!\n\n"
                            f"🆔 ID ЧАТА: {chat_id}\n"
                            f"👤 ОТ: @{from_user or 'Неизвестно'}\n\n"
                            f"📩 ТЕКСТ СООБЩЕНИЯ:\n"
                            f"────────────────────\n"
                            f"{msg_text}\n"
                            f"────────────────────\n\n"
                            f"🕐 ВРЕМЯ: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                        )
                        
                        try:
                            await bot.send_message(chat_id=ADMIN_ID, text=report)
                            logger.info(f"✅ Отчет отправлен админу")
                        except Exception as e:
                            logger.error(f"❌ Ошибка отправки: {e}")
                    else:
                        logger.info(f"⚠️ Сообщение {msg_id} не найдено в кеше")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка в вебхуке: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
