// ===== ВЕРСИЯ 4.0 - БЕЗ CORS =====
console.log('🚀 RCON Client v4.0 (No CORS)');

// ===== КОНФИГ =====
// Используем относительный путь - данные берутся из docs/ папки
const DATA_PATH = '/TelegramBotFAKEDDOSFAKEFAKEFAKE/data';
const CACHE_BUSTER = Date.now();

// ===== ФУНКЦИЯ ЗАПРОСА БЕЗ КЭША =====
function fetchNoCache(url) {
    const separator = url.includes('?') ? '&' : '?';
    return fetch(`${url}${separator}_=${CACHE_BUSTER}`, {
        cache: 'no-cache',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    });
}

// ===== ДОБАВЛЕНИЕ В КОНСОЛЬ =====
function addLog(text, type = 'result') {
    const output = document.getElementById('consoleOutput');
    const time = new Date().toLocaleTimeString('ru-RU');
    const typeClass = type || 'result';
    const safeText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${typeClass}">${safeText.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ПРОВЕРКА БОТА =====
async function checkBotStatus() {
    try {
        const res = await fetchNoCache(`${DATA_PATH}/logs.json`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.length > 0) {
                document.getElementById('botStatus').innerHTML = `
                    <span class="status-dot online"></span>
                    <span>Бот активен (${data.length} команд)</span>
                `;
                return true;
            }
        }
        document.getElementById('botStatus').innerHTML = `
            <span class="status-dot offline"></span>
            <span>Бот офлайн</span>
        `;
        return false;
    } catch (e) {
        document.getElementById('botStatus').innerHTML = `
            <span class="status-dot offline"></span>
            <span>Бот недоступен</span>
        `;
        return false;
    }
}

// ===== ОТПРАВКА КОМАНДЫ (ЧЕРЕЗ TELEGRAM) =====
function sendCommand(command) {
    if (!command) return;
    
    addLog(`$ ${command}`, 'command');
    addLog('📱 ОТПРАВЬ КОМАНДУ В TELEGRAM:', 'warning');
    addLog(`📝 Напиши боту @gredyr_bot: ${command}`, 'result');
    addLog('💡 Или в бизнес-чате с .help', 'info');
    addLog('⏳ Ответ придет в Telegram', 'warning');
    
    navigator.clipboard?.writeText(command).then(() => {
        addLog('📋 Команда скопирована! Вставь в Telegram', 'success');
    }).catch(() => {});
    
    document.getElementById('lastCommand').textContent = `⏳ Последняя: ${command}`;
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
    fetchNoCache(`${DATA_PATH}/logs.json`)
        .then(res => {
            if (!res.ok) throw new Error('No logs');
            return res.json();
        })
        .then(data => {
            if (data && data.length > 0) {
                const users = new Set(data.map(l => l.user_id));
                const probes = data.filter(l => l.command && l.command.includes('whois'));
                document.getElementById('statsUsers').textContent = `👤 Пользователей: ${users.size}`;
                document.getElementById('statsCommands').textContent = `📝 Команд: ${data.length}`;
                document.getElementById('statsProbes').textContent = `🔍 Пробивов: ${probes.length}`;
                document.getElementById('botStatus').innerHTML = `
                    <span class="status-dot online"></span>
                    <span>Бот активен (${data.length} команд)</span>
                `;
            }
        })
        .catch(() => {
            document.getElementById('statsUsers').textContent = '👤 Пользователей: -';
            document.getElementById('statsCommands').textContent = '📝 Команд: -';
            document.getElementById('statsProbes').textContent = '🔍 Пробивов: -';
            document.getElementById('botStatus').innerHTML = `
                <span class="status-dot offline"></span>
                <span>Бот офлайн</span>
            `;
        });
}

// ===== ОБНОВЛЕНИЕ ВРЕМЕНИ =====
function updateTime() {
    const now = new Date();
    const str = now.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    document.getElementById('currentTime').textContent = '🕐 ' + str;
}

// ===== ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ =====
function loadUsers() {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="users"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '👥 Пользователи';
    
    fetchNoCache(`${DATA_PATH}/logs.json`)
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
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="stats"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '📊 Статистика';
    
    fetchNoCache(`${DATA_PATH}/logs.json`)
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
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="blacklist"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '⛔ Черный список';
    
    fetchNoCache(`${DATA_PATH}/blacklist.json`)
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
    
    fetchNoCache(`${DATA_PATH}/logs.json`)
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
    console.log('🔧 Инициализация RCON v4.0...');
    updateTime();
    setInterval(updateTime, 1000);
    updateStatus();
    setInterval(updateStatus, 30000);
    checkBotStatus();
    setInterval(checkBotStatus, 60000);
    
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
    
    console.log(`📁 DATA_PATH: ${DATA_PATH}`);
    console.log('✅ RCON готов к работе!');
    console.log('💡 Команды отправляй через Telegram бота @gredyr_bot');
});
