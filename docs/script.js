// ===== ВЕРСИЯ 4.0 - ПРЯМОЙ ЗАПРОС К TELEGRAM API =====
console.log('🚀 RCON Client v4.0');

// ===== КОНФИГ =====
const BOT_TOKEN = '8883586607:AAFFMFAzP2az6O76DpV8p9DwuGUawMlUVn0';  // ВСТАВЬ СВОЙ ТОКЕН!
const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;
const ADMIN_ID = 8308522569;  // ТВОЙ ID

// ===== ДОБАВЛЕНИЕ В КОНСОЛЬ =====
function addLog(text, type = 'result') {
    const output = document.getElementById('consoleOutput');
    const time = new Date().toLocaleTimeString('ru-RU');
    const safeText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${type}">${safeText.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ОТПРАВКА КОМАНДЫ ЧЕРЕЗ TELEGRAM API =====
async function sendCommand(command) {
    if (!command) return;
    
    addLog(`$ ${command}`, 'command');
    addLog('⏳ Отправка команды...', 'warning');
    
    try {
        // Отправляем команду в Telegram
        const res = await fetch(`${TELEGRAM_API}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: ADMIN_ID,
                text: command,
                parse_mode: 'HTML'
            })
        });
        
        const data = await res.json();
        
        if (data.ok) {
            addLog('✅ Команда отправлена в Telegram!', 'success');
            addLog('📱 Проверь ответ в Telegram боте', 'warning');
            addLog(`📝 Команда: ${command}`, 'result');
        } else {
            addLog(`❌ Ошибка: ${data.description || 'Неизвестная ошибка'}`, 'error');
        }
        
    } catch (err) {
        addLog(`❌ Ошибка: ${err.message}`, 'error');
    }
}

function sendCommandFromInput() {
    const input = document.getElementById('commandInput');
    const cmd = input.value.trim();
    if (cmd) {
        sendCommand(cmd);
        input.value = '';
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 RCON Client v4.0 готов');
    
    document.getElementById('commandInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendCommandFromInput();
        }
    });
});
