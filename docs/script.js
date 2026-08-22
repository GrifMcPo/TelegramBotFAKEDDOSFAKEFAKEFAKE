// ===== КОНФИГ =====
const GITHUB_RAW = 'https://raw.githubusercontent.com/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/main/docs/data';
const GITHUB_API = 'https://api.github.com/repos/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/contents/docs/data';
const CACHE_BUSTER = Date.now();

// ===== ПЕРЕМЕННЫЕ =====
let commandId = 0;
let isWaitingResponse = false;

// ===== ФУНКЦИЯ ЗАПРОСА =====
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
    const safeText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${type}">${safeText.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ПРОВЕРКА БОТА =====
function updateBotStatus(online) {
    const status = document.getElementById('botStatus');
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

// ===== ОТПРАВКА КОМАНДЫ =====
async function sendCommand(command) {
    if (!command || isWaitingResponse) return;
    
    commandId++;
    const currentId = commandId;
    isWaitingResponse = true;
    
    addLog(`$ ${command}`, 'command');
    
    try {
        // 1. Пишем команду
        const commandData = { id: currentId, command: command };
        
        const fileRes = await fetch(`${GITHUB_API}/commands.json`, {
            headers: { 'Accept': 'application/vnd.github.v3+json' }
        });
        
        let sha = null;
        if (fileRes.ok) {
            const fileData = await fileRes.json();
            sha = fileData.sha;
        }
        
        const updateRes = await fetch(`${GITHUB_API}/commands.json`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `RCON: ${command}`,
                content: btoa(unescape(encodeURIComponent(JSON.stringify(commandData, null, 2)))),
                sha: sha
            })
        });
        
        if (!updateRes.ok) throw new Error('Ошибка отправки');
        
        // 2. Ждем ответ
        let attempts = 0;
        let response = null;
        
        while (attempts < 20) {
            await new Promise(r => setTimeout(r, 2000));
            
            const respRes = await fetchNoCache(`${GITHUB_RAW}/response.json`);
            if (respRes.ok) {
                const data = await respRes.json();
                if (data.id === currentId && data.status === 'done') {
                    response = data;
                    break;
                }
            }
            attempts++;
        }
        
        if (response) {
            addLog(response.result, 'result');
            updateBotStatus(true);
        } else {
            addLog('⏳ Команда отправлена, ответ не получен', 'warning');
        }
        
    } catch (err) {
        addLog(`❌ ${err.message}`, 'error');
        updateBotStatus(false);
    }
    
    isWaitingResponse = false;
}

function sendCommandFromInput() {
    const input = document.getElementById('commandInput');
    const cmd = input.value.trim();
    if (cmd) {
        sendCommand(cmd);
        input.value = '';
    }
}

// ===== ОБНОВЛЕНИЕ ВРЕМЕНИ =====
function updateTime() {
    const now = new Date();
    document.getElementById('currentTime').textContent = '🕐 ' + now.toLocaleString('ru-RU');
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    updateTime();
    setInterval(updateTime, 1000);
    updateBotStatus(true);
    
    document.getElementById('commandInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendCommandFromInput();
        }
    });
    
    console.log('🚀 RCON готов');
});
