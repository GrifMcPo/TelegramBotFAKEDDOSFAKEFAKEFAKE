// =============== НАСТРОЙКИ ===============
const SUPABASE_URL = 'https://txyvftkhmdavtajcfkdx.supabase.co';
const SUPABASE_KEY = 'sb_publishable_NGvqSLKswBzGx2s5s_IGCw_zM6Ct7n3';

// Создаем клиента Supabase
const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// Находим элементы DOM
const commandInput = document.getElementById('command-input');
const sendBtn = document.getElementById('send-btn');
const responseArea = document.getElementById('response-area');

async function sendCommand() {
    const text = commandInput.value.trim();
    
    if (!text) return;

    // Блокируем интерфейс
    sendBtn.disabled = true;
    sendBtn.textContent = 'Отправка...';
    responseArea.style.display = 'none';

    try {
        // 1. Записываем команду в таблицу commands
        const { error: cmdError } = await supabase.from('commands').insert({
            command: text,
        });

        if (cmdError) throw new Error(cmdError.message || 'Ошибка записи команды');

        // 2. Ожидаем появления ответа от бота (поллинг)
        let attempts = 0;
        const interval = setInterval(async () => {
            attempts++;
            
            // Ищем нашу свежую запись по тексту команды
            const { data: checkData, error: checkError } = await supabase
                .from('commands')
                .select('response_id')
                .eq('command', text)
                .order('created_at', { ascending: false })
                .limit(1)
                .single();

            if (checkError) {
                clearInterval(interval);
                showResult(`❌ Ошибка БД: ${checkError.message}`, true);
                return;
            }

            // Если bot.py прописал response_id — значит ответ готов
            if (checkData && checkData.response_id) {
                clearInterval(interval);
                
                // Забираем результат выполнения
                const { data: respData, error: respError } = await supabase
                    .from('responses')
                    .select('result, time')
                    .eq('id', checkData.response_id)
                    .single();

                if (respError) {
                    showResult(`❌ Ошибка получения: ${respError.message}`, true);
                } else {
                    showResult(respData.result + '\n\n⏱ Время: ' + respData.time, false);
                }
            } else if (attempts > 20) {
                // Таймаут 20 секунд
                clearInterval(interval);
                showResult('⚠️ Бот не ответил за 20 секунд.', true);
            }
        }, 1000); 

    } catch (err) {
        console.error(err);
        showResult('Критическая ошибка сети.', true);
    } finally {
        sendBtn.disabled = false;
        sendBtn.
