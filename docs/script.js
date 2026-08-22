// ==========================================
//       СЮДА ВСТАВЬТЕ ВАШИ КЛЮЧИ SUPABASE
// ==========================================
const supabaseUrl = 'https://txyvftkhmdavtajcfkdx.supabase.co'; // Ваш URL проекта
const supabaseKey = 'sb_publishable_NGvqSLKswBzGx2s5s_IGCw_zM6Ct7n3'; // Ваш Publishable Key

let requestIdCounter = 1;
const consoleDiv = document.getElementById('console');
const inputField = document.getElementById('cmdInput');
const sendBtn = document.getElementById('sendBtn');

function addLog(text, type = 'info') {
    const time = new Date().toLocaleTimeString();
    const colors = { info: '#93c5fd', success: '#bbf7d0', error: '#fecaca' };
    
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="timestamp">[${time}]</span> <span style="color:${colors[type]}">${text}</span>`;
    consoleDiv.appendChild(line);
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

async function sendCommand() {
    const cmd = inputField.value.trim();
    if (!cmd) return;

    const currentId = requestIdCounter++;
    addLog(`&gt; ${cmd}`, 'info');
    inputField.value = '';
    sendBtn.disabled = true;
    sendBtn.textContent = 'ОТПРАВКА...';

    try {
        // 1. Отправляем команду в таблицу commands
        await fetch(`${supabaseUrl}/rest/v1/commands`, {
            method: 'POST',
            headers: {
                apikey: supabaseKey,
                Authorization: `Bearer ${supabaseKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: cmd })
        });

        addLog("✅ Команда отправлена ботом", 'success');

        // 2. Начинаем ждать ответ в таблице responses
        let attempts = 0;
        const interval = setInterval(async () => {
            attempts++;
            
            const res = await fetch(`${supabaseUrl}/rest/v1/responses?response_id=eq.${currentId}&select=result,time`, {
                headers: { apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}` }
            });
            
            const data = await res.json();
            
            if (data && data.length > 0) {
                clearInterval(interval);
                
                // Очищаем старые попытки этого же запроса, если они были
                consoleDiv.querySelectorAll('.log-line').forEach(el => {
                    if (el.innerText.includes(`ID:${currentId}`) && el.innerText.includes('[BOT]')) {
                        el.remove();
                    }
                });

                addLog(`[BOT] ${data[0].result.replace(/\n/g, '<br>')}`, 'success');
                sendBtn.disabled = false;
                sendBtn.textContent = 'EXECUTE';
            } 
            
            // Таймаут ожидания
            if (attempts > 30) { 
                clearInterval(interval);
                addLog('⏰ Время ожидания истекло.', 'error');
                sendBtn.disabled = false;
                sendBtn.textContent = 'EXECUTE';
            }
        }, 1000); // Проверяем раз в секунду
        
    } catch (err) {
        addLog(`❌ Сетевая ошибка: ${err.message}`, 'error');
        sendBtn.disabled = false;
        sendBtn.textContent = 'EXECUTE';
    }
}

document.getElementById('cmdInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendCommand();
});

sendBtn.addEventListener('click', sendCommand);
