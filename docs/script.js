// ===== КОНФИГ =====
const GITHUB_RAW = 'https://raw.githubusercontent.comGrifMcPo/TelegramBotFAKEDDOS/main';
const GITHUB_API = 'https://api.github.com/repos/GrifMcPo/TelegramBotFAKEDDOS/contents';

// ===== ПЕРЕМЕННЫЕ =====
let commandId = 0;
let isWaitingResponse = false;

// ===== ДОБАВЛЕНИЕ В КОНСОЛЬ =====
function addLog(text, type = 'result') {
    const output = document.getElementById('consoleOutput');
    const time = new Date().toLocaleTimeString('ru-RU');
    const typeClass = type || 'result';
    const safeText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${typeClass}">${safeText.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ОТПРАВКА КОМАНДЫ ЧЕРЕЗ ФАЙЛ =====
async function sendCommand(command) {
    if (!command || isWaitingResponse) return;
    
    commandId++;
    const currentId = commandId;
    isWaitingResponse = true;
    
    addLog(`$ ${command}`, 'command');
    addLog('⏳ Отправка команды...', 'warning');
    
    try {
        // 1. Пишем команду в commands.json
        const commandData = {
            id: currentId,
            command: command
        };
        
        // Получаем текущий файл
        const fileRes = await fetch(`${GITHUB_API}/commands.json`, {
            headers: { 'Accept': 'application/vnd.github.v3+json' }
        });
        
        let sha = null;
        let currentContent = '';
        if (fileRes.ok) {
            const fileData = await fileRes.json();
            sha = fileData.sha;
            if (fileData.content) {
                try {
                    const decoded = atob(fileData.content);
                    currentContent = decoded;
                } catch(e) {}
            }
        }
        
        // Обновляем файл
        const updateRes = await fetch(`${GITHUB_API}/commands.json`, {
            method: 'PUT',
            headers: {
                'Authorization': `token ${GITHUB_TOKEN}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: `RCON command: ${command}`,
                content: btoa(unescape(encodeURIComponent(JSON.stringify(commandData, null, 2)))),
                sha: sha
            })
        });
        
        if (!updateRes.ok) {
            throw new Error('Failed to write command');
        }
        
        // 2. Ждем ответ
        let attempts = 0;
        let response = null;
        let lastLogs = [];
        
        while (attempts < 30) {
            await new Promise(r => setTimeout(r, 2000));
            
            // Проверяем response.json
            const respRes = await fetch(`${GITHUB_RAW}/response.json`);
            if (respRes.ok) {
                const data = await respRes.json();
                if (data.id === currentId && data.status === 'done') {
                    response = data;
                    break;
                }
            }
            
            // Проверяем логи на наличие новой записи
            if (attempts % 3 === 0) {
                const logRes = await fetch(`${GITHUB_RAW}/logs.json`);
                if (logRes.ok) {
                    const logs = await logRes.json();
                    if (logs.length > lastLogs.length) {
                        const newLogs = logs.slice(lastLogs.length);
                        for (const log of newLogs) {
                            if (log.command === command) {
                                response = {
                                    result: `✅ Команда выполнена (логи обновлены)`,
                                    time: log.time || new Date().toISOString()
                                };
                                break;
                            }
                        }
                        lastLogs = logs;
                    }
                }
            }
            attempts++;
        }
        
        // Убираем "Отправка..."
        const output = document.getElementById('consoleOutput');
        const entries = output.querySelectorAll('.log-entry');
        for (const entry of entries) {
            if (entry.textContent.includes('⏳ Отправка команды...')) {
                entry.remove();
                break;
            }
        }
        
        if (response) {
            addLog(`📥 ${response.result}`, 'result');
            updateStatus();
            document.getElementById('lastCommand').textContent = `⏳ Последняя: ${command}`;
        } else {
            addLog('❌ Таймаут: бот не ответил (проверьте logs.json)', 'error');
        }
        
    } catch (err) {
        const output = document.getElementById('consoleOutput');
        const entries = output.querySelectorAll('.log-entry');
        for (const entry of entries) {
            if (entry.textContent.includes('⏳ Отправка команды...')) {
                entry.remove();
                break;
            }
        }
        addLog(`❌ Ошибка: ${err.message}`, 'error');
        addLog('💡 Проверьте: бот запущен в GitHub Actions?', 'warning');
    }
    
    isWaitingResponse = false;
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
    fetch(`${GITHUB_RAW}/logs.json`)
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
    sendCommand('/idlist');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="users"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '👥 Пользователи';
}

function loadStats() {
    sendCommand('/stats');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="stats"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '📊 Статистика';
}

function loadBlacklist() {
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-page="blacklist"]')?.classList.add('active');
    document.getElementById('pageTitle').textContent = '⛔ Черный список';
    
    fetch(`${GITHUB_RAW}/blacklist.json`)
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
    
    fetch(`${GITHUB_RAW}/logs.json`)
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
    updateTime();
    setInterval(updateTime, 1000);
    updateStatus();
    setInterval(updateStatus, 30000);
    
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
    
    console.log('🚀 RCON Client loaded');
    console.log(`📁 GitHub RAW: ${GITHUB_RAW}`);
});
