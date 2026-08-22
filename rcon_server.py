from flask import Flask, request, jsonify, render_template, session
import json
import os
import sys
from datetime import datetime, timedelta
from functools import wraps

# Добавляем путь к боту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем функции из бота
from bot import execute_rcon_command, get_all_users, get_logs_for_user, get_msk_time

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'your_secret_key_here')

# Настройки
RCON_PASSWORD = os.getenv('RCON_PASSWORD', 'admin123')

# Декоратор для проверки авторизации
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized', 'status': 'error'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    """Главная страница - RCON консоль"""
    if not session.get('logged_in'):
        return render_template('rcon.html', logged_in=False)
    return render_template('rcon.html', logged_in=True)

@app.route('/login', methods=['POST'])
def login():
    """Авторизация в RCON"""
    password = request.json.get('password', '')
    if password == RCON_PASSWORD:
        session['logged_in'] = True
        return jsonify({'status': 'success', 'message': 'Авторизация успешна'})
    return jsonify({'status': 'error', 'message': 'Неверный пароль'}), 401

@app.route('/logout')
def logout():
    """Выход из RCON"""
    session.pop('logged_in', None)
    return jsonify({'status': 'success', 'message': 'Выход выполнен'})

@app.route('/api/command', methods=['POST'])
@require_auth
def execute_command():
    """Выполнение команды через RCON"""
    data = request.json
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({'status': 'error', 'message': 'Команда не указана'}), 400
    
    # Выполняем команду
    result = execute_rcon_command(command)
    
    return jsonify({
        'status': 'success',
        'command': command,
        'result': result,
        'time': get_msk_time()
    })

@app.route('/api/users', methods=['GET'])
@require_auth
def get_users():
    """Получить список пользователей"""
    users = get_all_users()
    return jsonify({
        'status': 'success',
        'users': users,
        'count': len(users)
    })

@app.route('/api/logs/<identifier>', methods=['GET'])
@require_auth
def get_user_logs(identifier):
    """Получить логи пользователя"""
    logs = get_logs_for_user(identifier)
    return jsonify({
        'status': 'success',
        'identifier': identifier,
        'logs': logs,
        'count': len(logs)
    })

@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Получить статистику"""
    try:
        with open('logs.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)
        users = set(l.get('user_id') for l in logs)
        probes = len([l for l in logs if 'whois' in l.get('command', '').lower()])
        return jsonify({
            'status': 'success',
            'users': len(users),
            'commands': len(logs),
            'probes': probes,
            'time': get_msk_time()
        })
    except:
        return jsonify({
            'status': 'error',
            'message': 'Статистика недоступна'
        }), 500

@app.route('/api/blacklist', methods=['GET'])
@require_auth
def get_blacklist():
    """Получить черный список"""
    try:
        with open('blacklist.json', 'r', encoding='utf-8') as f:
            blacklist = json.load(f)
        return jsonify({
            'status': 'success',
            'blacklist': blacklist,
            'count': len(blacklist)
        })
    except:
        return jsonify({
            'status': 'error',
            'message': 'Черный список недоступен'
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🔥 RCON СЕРВЕР ЗАПУЩЕН!")
    print(f"🌐 Адрес: http://localhost:5000")
    print(f"🔑 Пароль: {RCON_PASSWORD}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
