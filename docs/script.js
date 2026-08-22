// ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
let isLoggedIn = false;

// ===== ПРОВЕРКА АВТОРИЗАЦИИ =====
function checkAuth() {
    fetch('/api/stats')
        .then(res => {
            if (res.status === 401) {
                document.getElementById('loginScreen').style.display = 'flex';
                document.getElementById('mainApp').style.display = 'none';
                isLoggedIn = false;
            } else {
                document.getElementById('loginScreen').style.display = 'none';
                document.getElementById('mainApp').style.display = 'flex';
                isLoggedIn = true;
                updateStatus();
                updateTime();
            }
        })
        .catch(() => {
            // Если сервер недоступен - показываем логин
            document.getElementById('loginScreen').style.display = 'flex';
            document.getElementById('mainApp').style.display = 'none';
        });
}

// ===== ЛОГИН =====
function login() {
    const password = document.getElementById('passwordInput').value;
    const errorEl = document.getElementById('loginError');
    
    if (!password) {
        errorEl.textContent = '❌ Введите пароль';
        return;
    }
    
    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: password })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            errorEl.textContent = '';
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('mainApp').style.display = 'flex';
            isLoggedIn = true;
            updateStatus();
            updateTime();
            addLog('✅ Авторизация успешна', 'success');
        } else {
            errorEl.textContent = '❌ ' + data.message;
        }
    })
    .catch(() => {
        errorEl.textContent = '❌ Ошибка соединения с сервером';
    });
}

// ===== ВЫХОД =====
function logout() {
    fetch('/logout')
        .then(() => {
            document.getElementById('loginScreen').style.display = 'flex';
            document.getElementById('mainApp').style.display = 'none';
            isLoggedIn = false;
        });
}

// ===== ДОБАВЛЕНИЕ В КОНСОЛЬ =====
function addLog(text, type = 'result') {
    const output = document.getElementById('consoleOutput');
    const time = new Date().toLocaleTimeString('ru-RU');
    const typeClass = type || 'result';
    
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${typeClass}">${text.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ОТПРАВКА КОМАНДЫ =====
function sendCommand(command) {
    if (!command || !isLoggedIn) return;
    
    const time = new Date().toLocaleTimeString('ru-RU');
    addLog(`$ ${command}`, 'command');
    
    fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: command })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            addLog(data.result, 'result');
        } else {
            addLog(`❌ ${data.message || 'Ошибка'}`, 'error');
        }
        updateStatus();
    })
    .catch(err => {
        addLog(`❌ Ошибка соединения: ${err.message}`, 'error');
    });
}

function sendCommandFromInput() {
    const input = document.getElementById('commandInput');
    const command = input.value.trim();
    if (command) {
        sendCommand(command);
        input.value = '';
    }
}

// ===== ОБНОВЛЕНИЕ СТАТУСА =====
function updateStatus() {
    if (!isLoggedIn) return;
    
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('statsUsers').textContent = `👤 Пользователей: ${data.users}`;
                document.getElementById('statsCommands').textContent = `📝 Команд: ${data.commands}`;
                document.getElementById('statsProbes').textContent = `🔍 Пробивов: ${data.probes}`;
            }
        })
        .catch(() => {});
}

// ===== ОБНОВЛЕНИЕ ВРЕМЕНИ =====
function updateTime() {
    const now = new Date();
    const str = now.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('currentTime').textContent = '🕐 ' + str;
}

// ===== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ =====
function loadUsers() {
    sendCommand('/idlist');
}

// ===== ЗАГРУЗКА СТАТИСТИКИ =====
function loadStats() {
    sendCommand('/stats');
}

// ===== ЗАГРУЗКА ЧЕРНОГО СПИСКА =====
function loadBlacklist() {
    if (!isLoggedIn) return;
    
    fetch('/api/blacklist')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                let result = '⛔ ЧЕРНЫЙ СПИСОК\n\n';
                if (data.count === 0) {
                    result += '📭 Черный список пуст';
                } else {
                    for (const [uid, info] of Object.entries(data.blacklist)) {
                        result += `🆔 ${uid}\n`;
                        result += `📌 Причина: ${info.reason || 'Не указана'}\n`;
                        result += `👤 Добавил: ${info.added_by || 'Неизвестно'}\n`;
                        result += `🕐 Время: ${info.added_at || 'Неизвестно'}\n`;
                        if (info.expires_at) {
                            result += `⏱ Истекает: ${info.expires_at}\n`;
                        }
                        result += '─' * 20 + '\n';
                    }
                }
                addLog(result, 'result');
            } else {
                addLog(`❌ ${data.message || 'Ошибка загрузки черного списка'}`, 'error');
            }
        })
        .catch(err => {
            addLog(`❌ Ошибка: ${err.message}`, 'error');
        });
}

// ===== ПОИСК ЛОГОВ =====
function showLogsPanel() {
    const panel = document.getElementById('logsPanel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        document.getElementById('logsResult').innerHTML = '';
    } else {
        panel.style.display = 'none';
    }
}

function searchLogs() {
    const query = document.getElementById('logsSearch').value.trim();
    if (!query) {
        document.getElementById('logsResult').innerHTML = '❌ Введите ID или @username';
        return;
    }
    
    fetch(`/api/logs/${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            const resultEl = document.getElementById('logsResult');
            if (data.status === 'success') {
                if (data.count === 0) {
                    resultEl.innerHTML = `❌ Логи не найдены для ${data.identifier}`;
                    return;
                }
                let html = `📊 ЛОГИ ДЛЯ: ${data.identifier}\n`;
                html += `📝 Всего команд: ${data.count}\n`;
                html += `🕐 За последние 5 дней\n\n`;
                html += '─'.repeat(30) + '\n\n';
                
                data.logs.slice(-50).forEach(log => {
                    html += `🕐 ${log.time || 'Нет времени'}\n`;
                    html += `📝 ${log.command || 'Неизвестно'}\n`;
                    if (log.target) html += `🎯 ${log.target}\n`;
                    html += '─'.repeat(20) + '\n';
                });
                
                resultEl.innerHTML = html.replace(/\n/g, '<br>');
            } else {
                resultEl.innerHTML = `❌ ${data.message || 'Ошибка'}`;
            }
        })
        .catch(err => {
            document.getElementById('logsResult').innerHTML = `❌ Ошибка: ${err.message}`;
        });
}

// ===== НАВИГАЦИЯ =====
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function(e) {
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        this.classList.add('active');
        
        const page = this.dataset.page;
        const titles = {
            'console': '💻 RCON Консоль',
            'users': '👥 Пользователи',
            'stats': '📊 Статистика',
            'blacklist': '⛔ Черный список',
            'logs': '📝 Логи'
        };
        document.getElementById('pageTitle').textContent = titles[page] || 'RCON';
    });
});

// ===== ИНИЦИАЛИЗАЦИЯ =====
// Проверяем авторизацию при загрузке
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    setInterval(updateTime, 1000);
    setInterval(updateStatus, 30000);
    
    // Если нажали Enter в поле ввода
    document.getElementById('commandInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendCommandFromInput();
        }
    });
    
    // Автоматический вход по Enter на странице логина
    document.getElementById('passwordInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            login();
        }
    });
});

// Если страница загружена, проверяем авторизацию
console.log('🚀 RCON Client loaded');
