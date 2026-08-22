// ===== ВЕРСИЯ 3.0 =====
console.log('🚀 RCON Client v3.0');

// ===== КОНФИГ =====
const GITHUB_RAW = 'https://raw.githubusercontent.com/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/main/docs/data';
const CACHE_BUSTER = Date.now();

// ===== ДОБАВЛЕНИЕ В КОНСОЛЬ =====
function addLog(text, type = 'result') {
    const output = document.getElementById('consoleOutput');
    const time = new Date().toLocaleTimeString('ru-RU');
    const safeText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${type}">${safeText.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ПРОВЕРКА БОТА =====
function updateBotStatus(online) {
    const status = document.getElementById('botStatus');
    if (status) {
        if (online) {
            status.textContent = '🟢 Бот активен';
            status.style.color = '#00ff88';
            status.style.borderColor = 'rgba(0, 255, 136, 0.2)';
        } else {
            status.textContent = '🔴 Бот офлайн';
            status.style.color = '#ff4444';
            status.style.borderColor = 'rgba(255, 68, 68, 0.2)';
        }
    }
}

// ===== ОБНОВЛЕНИЕ СТАТУСА ИЗ ЛОГОВ =====
function updateStatus() {
    fetch(`${GITHUB_RAW}/logs.json?_=${CACHE_BUSTER}`, {
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
    })
        .then(res => {
            if (!res.ok) throw new Error('No logs');
            return res.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                updateBotStatus(true);
            }
        })
        .catch(() => {
            updateBotStatus(false);
        });
}

// ===== ОТПРАВКА КОМАНДЫ ЧЕРЕЗ TELEGRAM =====
function sendCommand(command) {
    if (!command) return;
    
    addLog(`$ ${command}`, 'command');
    addLog('📱 ОТПРАВЬ КОМАНДУ В TELEGRAM:', 'warning');
    addLog(`📝 Напиши боту @gredyr_bot: ${command}`, 'result');
    addLog('💡 Или в бизнес-чате с .help', 'info');
    addLog('⏳ Ответ придет в Telegram', 'warning');
    
    // Копируем в буфер
    navigator.clipboard?.writeText(command).then(() => {
        addLog('📋 Команда скопирована! Вставь в Telegram', 'success');
    }).catch(() => {});
    
    document.getElementById('lastCommand').textContent = `⏳ Последняя: ${command}`;
}

function sendCommandFromInput() {
    const input = document.getElementById('commandInput');
    const cmd = input.value.trim();
    if (cmd) {
        sendCommand(cmd);
        input.value = '';
    }
}

// ===== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ =====
function loadUsers() {
    fetch(`${GITHUB_RAW}/logs.json?_=${CACHE_BUSTER}`, {
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
    })
        .then(res => {
            if (!res.ok) throw new Error('No logs');
            return res.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                const users = {};
                data.forEach(log => {
                    if (log.user_id) {
                        users[log.user_id] = {
                            username: log.username || 'Нет',
                            full_name: log.full_name || 'Нет'
                        };
                    }
                });
                
                let result = '👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ\n\n';
                for (const [uid, info] of Object.entries(users)) {
                    result += `🆔 ${uid}\n`;
                    if (info.username !== 'Нет') result += `👤 @${info.username}\n`;
                    if (info.full_name !== 'Нет') result += `📛 ${info.full_name}\n`;
                    result += '─'.repeat(20) + '\n';
                }
                addLog(result, 'result');
            } else {
                addLog('📊 Нет пользователей в логах', 'result');
            }
        })
        .catch(err => {
            addLog(`❌ Ошибка: ${err.message}`, 'error');
        });
}

function loadStats() {
    fetch(`${GITHUB_RAW}/logs.json?_=${CACHE_BUSTER}`, {
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
    })
        .then(res => {
            if (!res.ok) throw new Error('No logs');
            return res.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                const users = new Set(data.map(l => l.user_id));
                const probes = data.filter(l => l.command && l.command.includes('whois'));
                addLog(`📊 СТАТИСТИКА\n\n👤 Пользователей: ${users.size}\n📝 Команд: ${data.length}\n🔍 Пробивов: ${probes.length}\n🕐 Время: ${new Date().toLocaleString('ru-RU')}`, 'result');
            } else {
                addLog('📊 Нет данных', 'result');
            }
        })
        .catch(err => {
            addLog(`❌ Ошибка: ${err.message}`, 'error');
        });
}

function loadBlacklist() {
    fetch(`${GITHUB_RAW}/blacklist.json?_=${CACHE_BUSTER}`, {
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
    })
        .then(res => {
            if (!res.ok) throw new Error('Blacklist unavailable');
            return res.json();
        })
        .then(data => {
            let result = '⛔ ЧЕРНЫЙ СПИСОК\n\n';
            if (Object.keys(data).length === 0) {
                result += '📭 Черный список пуст';
            } else {
                for (const [uid, info] of Object.entries(data)) {
                    result += `🆔 ID: ${uid}\n`;
                    result += `📌 Причина: ${info.reason || 'Не указана'}\n`;
                    result += `👤 Добавил: ${info.added_by || 'Неизвестно'}\n`;
                    result += `🕐 Время: ${info.added_at || 'Неизвестно'}\n`;
                    if (info.expires_at) {
                        result += `⏱ Истекает: ${info.expires_at}\n`;
                    }
                    result += '─'.repeat(20) + '\n';
                }
            }
            addLog(result, 'result');
        })
        .catch(err => {
            addLog(`❌ Ошибка: ${err.message}`, 'error');
        });
}

// ===== НАВИГАЦИЯ =====
function showConsole() {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="console"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '💻 RCON Консоль';
    document.getElementById('logsPanel').style.display = 'none';
}

function showLogsPanel() {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="logs"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '📝 Логи';
    const panel = document.getElementById('logsPanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    document.getElementById('logsResult').innerHTML = '';
}

function searchLogs() {
    const query = document.getElementById('logsSearch').value.trim();
    if (!query) {
        document.getElementById('logsResult').innerHTML = '❌ Введите ID или @username';
        return;
    }
    
    document.getElementById('logsResult').innerHTML = '⏳ Загрузка...';
    
    fetch(`${GITHUB_RAW}/logs.json?_=${CACHE_BUSTER}`, {
        cache: 'no-cache',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
    })
        .then(res => {
            if (!res.ok) throw new Error('Logs unavailable');
            return res.json();
        })
        .then(data => {
            const resultEl = document.getElementById('logsResult');
            if (!data || data.length === 0) {
                resultEl.innerHTML = '❌ Логи не найдены';
                return;
            }
            
            const filtered = data.filter(log => {
                const idMatch = log.user_id && String(log.user_id) === query;
                const nameMatch = log.username && log.username.toLowerCase().includes(query.toLowerCase().replace('@', ''));
                return idMatch || nameMatch;
            });
            
            if (filtered.length === 0) {
                resultEl.innerHTML = `❌ Логи не найдены для ${query}`;
                return;
            }
            
            let html = `📊 ЛОГИ ДЛЯ: ${query}\n`;
            html += `📝 Всего команд: ${filtered.length}\n`;
            html += `🕐 За последние 5 дней\n\n`;
            html += '─'.repeat(30) + '\n\n';
            
            filtered.slice(-50).forEach(log => {
                html += `🕐 ${log.time || 'Нет времени'}\n`;
                html += `📝 ${log.command || 'Неизвестно'}\n`;
                if (log.target) html += `🎯 ${log.target}\n`;
                html += '─'.repeat(20) + '\n';
            });
            
            resultEl.innerHTML = html.replace(/\n/g, '<br>');
        })
        .catch(err => {
            document.getElementById('logsResult').innerHTML = `❌ Ошибка: ${err.message}`;
        });
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Инициализация RCON v3.0...');
    updateStatus();
    setInterval(updateStatus, 30000);
    
    // Обновляем статус бота
    updateBotStatus(true);
    
    document.getElementById('commandInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendCommandFromInput();
        }
    });
    
    document.getElementById('logsSearch').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            searchLogs();
        }
    });
    
    console.log(`📁 GITHUB_RAW: ${GITHUB_RAW}`);
    console.log('✅ RCON готов к работе!');
});
