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
    sendBtn.textContent = 'ЖДЕМ...';

    try {
        // 1. Отправляем команду
        const postRes = await fetch(`${supabaseUrl}/rest/v1/commands`, {
            method: 'POST',
            headers: {
                apikey: supabaseKey,
                Authorization: `Bearer ${supabaseKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: cmd })
        });

        if (!postRes.ok) {
            const errText = await postRes.text();
            throw new Error(`Supabase POST error: ${errText}`);
        }

        // 2. Опрос таблицы responses
        let attempts = 0;
        const interval = setInterval(async () => {
            attempts++;
            
            try {
                const res = await fetch(`${supabaseUrl}/rest/v1/responses?response_id=eq.${currentId}&select=result,time`, {
                    headers: { 
                        apikey: supabaseKey, 
                        Authorization: `Bearer ${supabaseKey}` 
                    }
                });

                if (!res.ok) throw new Error("Failed to fetch response");
                
                const data = await res.json();

                // Проверяем, пришел ли именно наш ответ
                if (data && Array.isArray(data) && data.length > 0) {
                    clearInterval(interval);
                    
                    // Удаляем заглушку "ЖДЕМ", чтобы не мусорить в логах
                    const lines = consoleDiv.querySelectorAll('.log-line');
                    const lastLine = lines[lines.length - 1];
                    if (lastLine && lastLine.innerText.includes(currentId) && lastLine.innerText.includes('ЖДЕМ')) {
                        lastLine.remove();
                    }

                    // Выводим красивый ответ от бота
                    const resultText = data[0].result || "[Пустой ответ]";
                    addLog(resultText.replace(/\n/g, '<br>'), 'success');
                
                } else if (attempts > 45) { // Таймаут ~45 секунд
                    clearInterval(interval);
                    addLog('⏰ Время ожидания истекло. Попробуйте снова.', 'error');
                }

            } catch (pollErr) {
                // Игнорируем мелкие сетевые сбои во время опроса
                if (attempts > 45) {
                    clearInterval(interval);
                    addLog('❌ Ошибка связи при ожидании ответа.', 'error');
                }
            }
        }, 1000); // Раз в секунду
        
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
