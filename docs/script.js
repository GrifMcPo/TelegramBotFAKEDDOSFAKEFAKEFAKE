// ===== ВЕРСИЯ 7.0 - SUPABASE РАБОТАЕТ! =====
console.log('🚀 RCON Client v7.0');

// ===== КОНФИГ SUPABASE =====
const SUPABASE_URL = 'https://txyvftkhmdavtajcfkdx.supabase.co';
const SUPABASE_KEY = 'sb_publishable_NGvqSLKswBzGx2s5s_IGCw_zM6Ct7n3';

// ===== ДОБАВЛЕНИЕ В КОНСОЛЬ =====
function addLog(text, type = 'result') {
    const output = document.getElementById('consoleOutput');
    const time = new Date().toLocaleTimeString('ru-RU');
    const safeText = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    output.innerHTML += `<div class="log-entry"><span class="time">[${time}]</span> <span class="${type}">${safeText.replace(/\n/g, '<br>')}</span></div>`;
    output.scrollTop = output.scrollHeight;
}

// ===== ФУНКЦИЯ ЗАПРОСА К SUPABASE =====
async function supabaseRequest(endpoint, method = 'GET', body = null) {
    const url = `${SUPABASE_URL}/rest/v1/${endpoint}`;
    const headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    };
    
    const options = {
        method: method,
        headers: headers
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const res = await fetch(url, options);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return await res.json();
    } catch (err) {
        throw new Error(`Ошибка запроса к Supabase: ${err.message}`);
    }
}

// ===== ОТПРАВКА КОМАНДЫ =====
async function sendCommand(command) {
    if (!command) return;
    
    addLog(`$ ${command}`, 'command');
    addLog('⏳ Отправка...', 'warning');
    
    try {
        // 1. Создаем запись в Supabase
        const result = await supabaseRequest('rcon_commands', 'POST', {
            command: command,
            status: 'waiting'
        });
        
        if (result && result.length > 0) {
            const commandId = result[0].id;
            addLog('✅ Команда отправлена, ждем ответ...', 'success');
            
            // 2. Ждем ответ
            let attempts = 0;
            let response = null;
            
            while (attempts < 25) {
                await new Promise(r => setTimeout(r, 2000));
                
                try {
                    const data = await supabaseRequest(`rcon_commands?id=eq.${commandId}&select=*`);
                    if (data && data.length > 0 && data[0].status === 'done') {
                        response = data[0];
                        break;
                    }
                } catch (e) {}
                attempts++;
            }
            
            // Убираем "Отправка..."
            const output = document.getElementById('consoleOutput');
            const entries = output.querySelectorAll('.log-entry');
            for (const entry of entries) {
                if (entry.textContent.includes('⏳ Отправка...')) {
                    entry.remove();
                    break;
                }
            }
            
            if (response && response.result) {
                addLog(response.result, 'result');
            } else {
                addLog('⏳ Команда отправлена, ответ не получен', 'warning');
            }
        } else {
            addLog('❌ Ошибка создания команды', 'error');
        }
        
    } catch (err) {
        const output = document.getElementById('consoleOutput');
        const entries = output.querySelectorAll('.log-entry');
        for (const entry of entries) {
            if (entry.textContent.includes('⏳ Отправка...')) {
                entry.remove();
                break;
            }
        }
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
    console.log('🚀 RCON v7.0 готов');
    console.log(`🔗 Supabase: ${SUPABASE_URL}`);
    
    document.getElementById('commandInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendCommandFromInput();
        }
    });
});
