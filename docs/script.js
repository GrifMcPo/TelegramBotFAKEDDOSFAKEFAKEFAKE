// ==========================================
//       СЮДА ВСТАВЬТЕ ВАШИ КЛЮЧИ SUPABASE
// ==========================================
const supabaseUrl = 'https://txyvftkhmdavtajcfkdx.supabase.co';
const supabaseKey = 'sb_publishable_NGvqSLKswBzGx2s5s_IGCw_zM6Ct7n3';

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
    sendBtn.textContent = 'ЖДЕМ ОТВЕТА...';

    try {
        // 1. Отправляем команду
        await fetch(`${supabaseUrl}/rest/v1/commands`, {
            method: 'POST',
            headers: {
                apikey: supabaseKey,
                Authorization: `Bearer ${supabaseKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: cmd })
        });

        // 2. Опрос таблицы responses 
        let attempts = 0;
        const interval = setInterval(async () => {
            attempts++;
            
            try {
                // ИСПРАВЛЕНИЕ ТУТ: фильтруем по response_id
                const res = await fetch(`${supabaseUrl}/rest/v1/responses?response_id=eq.${currentId}&select=result,time`, {
                    headers: { 
                        apikey: supabaseKey, 
                        Authorization: `Bearer ${supabaseKey}` 
                    }
                });

                if (!res.ok) throw new Error("Network failed");
                
                const data = await res.json();

                // Если массив не пустой - значит нашли наш ответ
                if (data && Array.isArray(data) && data.length > 0) {
                    clearInterval(interval);
                    
                    // Удаляем сообщение "ЖДЕМ", чтобы было чисто
                    const lines = consoleDiv.querySelectorAll('.log-line');
                    if (lines.length > 0) {
                        const lastLine = lines[lines.length - 1];
                        if (lastLine.innerText.includes(currentId) && lastLine.innerText.includes('ЖДЕМ')) {
                            lastLine.remove();
                        }
                    }

                    const resultText = data[0].result || "[Пустой ответ]";
                    addLog(resultText.replace(/\n/g, '<br>'), 'success');
                
                } else if (attempts > 45) {
                    clearInterval(interval);
                    addLog('⏰ Время ожидания истекло.', 'error');
                }

            } catch (e) {
                if (attempts > 45) {
                    clearInterval(interval);
                    addLog('❌ Ошибка связи.', 'error');
                }
            }
        }, 1000); 
        
    } catch (err) {
        addLog(`❌ Критическая ошибка: ${err.message}`, 'error');
        sendBtn.disabled = false;
        sendBtn.textContent = 'EXECUTE';
    }
}

document.getElementById('cmdInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendCommand();
});

sendBtn.addEventListener('click', sendCommand);
