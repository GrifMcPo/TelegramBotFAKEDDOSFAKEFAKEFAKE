// ============================================================
// КЛЮЧИ ДОСТУПА
// ============================================================
const VALID_KEYS = [
    'OWNER!KEY!_%!$W@$%OWENR!@#W$!($',
    'ADMIN!KEY!@#$%^&*()',
    'SUPER!ADMIN!KEY!12345',
    'BOSS!KEY!_!@#$%^&*',
    'MASTER!KEY!QWERTY123'
];

// ============================================================
// URL ДЛЯ ДАННЫХ
// ============================================================
// Используем raw.githubusercontent.com для доступа к файлам
const REPO_OWNER = 'GrifMcPo';
const REPO_NAME = 'TelegramBotFAKEDDOSFAKEFAKEFAKE';
const BRANCH = 'main';
const DATA_URL = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${BRANCH}/`;

// ============================================================
// ЭЛЕМЕНТЫ
// ============================================================
const loginPage = document.getElementById('loginPage');
const mainPage = document.getElementById('mainPage');
const keyInput = document.getElementById('keyInput');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');
const logoutBtn = document.getElementById('logoutBtn');

// ============================================================
// ВХОД
// ============================================================
function login() {
    const key = keyInput.value.trim();
    if (VALID_KEYS.includes(key)) {
        loginPage.style.display = 'none';
        mainPage.style.display = 'block';
        loginError.classList.remove('show');
        loadAllData();
        // Автообновление каждые 15 секунд
        setInterval(loadAllData, 15000);
    } else {
        loginError.classList.add('show');
        keyInput.value = '';
        keyInput.focus();
        setTimeout(() => loginError.classList.remove('show'), 3000);
    }
}

loginBtn.addEventListener('click', login);
keyInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') login(); });

logoutBtn.addEventListener('click', () => {
    mainPage.style.display = 'none';
    loginPage.style.display = 'flex';
    keyInput.value = '';
    keyInput.focus();
});

// ============================================================
// ТАБЫ
// ============================================================
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`tab-${tab}`).classList.add('active');
    });
});

// ============================================================
// ЗАГРУЗКА ДАННЫХ
// ============================================================
async function loadAllData() {
    await Promise.all([loadUsers(), loadStats(), loadChats()]);
}

async function loadUsers() {
    try {
        const url = DATA_URL + 'users.json?t=' + Date.now();
        console.log('📥 Загрузка users.json:', url);
        const response = await fetch(url);
        
        if (!response.ok) {
            console.warn('⚠️ users.json не найден (бот ещё не запускался)');
            document.getElementById('usersTableBody').innerHTML = '<tr><td colspan="4" class="loading-text">📭 Нет данных (бот ещё не запускался)</td></tr>';
            return;
        }
        
        const data = await response.json();
        console.log('✅ users.json загружен:', Object.keys(data).length, 'пользователей');
        
        const userIds = Object.keys(data);
        document.getElementById('statUsers').textContent = userIds.length;
        document.getElementById('statUptime').textContent = new Date().toLocaleTimeString('ru-RU');
        
        const tbody = document.getElementById('usersTableBody');
        if (userIds.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">📭 Нет подключенных пользователей</td></tr>';
            return;
        }
        
        tbody.innerHTML = userIds.map((id, i) => {
            const user = data[id];
            return `<tr><td>${i+1}</td><td>${id}</td><td>@${user.username || 'Нет'}</td><td>${user.connected_at || 'Неизвестно'}</td></tr>`;
        }).join('');
        
    } catch (error) {
        console.error('❌ Ошибка загрузки users.json:', error);
        document.getElementById('usersTableBody').innerHTML = '<tr><td colspan="4" class="loading-text">❌ Ошибка загрузки</td></tr>';
    }
}

async function loadStats() {
    try {
        const url = DATA_URL + 'stats.json?t=' + Date.now();
        console.log('📥 Загрузка stats.json:', url);
        const response = await fetch(url);
        
        if (!response.ok) {
            console.warn('⚠️ stats.json не найден');
            document.getElementById('statCommands').textContent = '0';
            document.getElementById('statStatus').textContent = '⏳ Ожидание';
            return;
        }
        
        const data = await response.json();
        console.log('✅ stats.json загружен');
        document.getElementById('statCommands').textContent = data.total_commands || 0;
        document.getElementById('statStatus').textContent = data.total_connections > 0 ? '🟢 Онлайн' : '🔴 Оффлайн';
        
    } catch (error) {
        console.error('❌ Ошибка загрузки stats.json:', error);
        document.getElementById('statCommands').textContent = '0';
        document.getElementById('statStatus').textContent = '⏳ Ожидание';
    }
}

async function loadChats() {
    try {
        const url = DATA_URL + 'users.json?t=' + Date.now();
        console.log('📥 Загрузка чатов из users.json');
        const response = await fetch(url);
        
        if (!response.ok) {
            document.getElementById('chatsContainer').innerHTML = '<div class="loading-text">📭 Нет данных (бот ещё не запускался)</div>';
            return;
        }
        
        const data = await response.json();
        const container = document.getElementById('chatsContainer');
        const userIds = Object.keys(data);
        
        if (userIds.length === 0) {
            container.innerHTML = '<div class="loading-text">📭 Нет чатов</div>';
            return;
        }
        
        container.innerHTML = userIds.map((id) => {
            const user = data[id];
            return `
                <div class="chat-card" onclick="showChatInfo('${id}')">
                    <div class="chat-username">@${user.username || 'Нет'}</div>
                    <div class="chat-id">🆔 ${id}</div>
                    <div class="chat-connected">📅 ${user.connected_at || 'Неизвестно'}</div>
                    <div class="chat-commands">📝 ${user.commands || 0} команд</div>
                    <span class="chat-status online">🟢 Активен</span>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('❌ Ошибка загрузки чатов:', error);
        document.getElementById('chatsContainer').innerHTML = '<div class="loading-text">❌ Ошибка загрузки</div>';
    }
}

function showChatInfo(chatId) {
    alert(`📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n🆔 ID: ${chatId}\n📌 Данные загружаются...\n🕐 ${new Date().toLocaleString('ru-RU')}`);
}

// ============================================================
// СТАТУС БОТА ПРОВЕРЯЕМ ЧЕРЕЗ HEADERS
// ============================================================
async function checkBotStatus() {
    try {
        const response = await fetch('https://api.telegram.org/bot' + BOT_TOKEN + '/getMe');
        if (response.ok) {
            document.getElementById('statStatus').textContent = '🟢 Онлайн';
        } else {
            document.getElementById('statStatus').textContent = '🔴 Оффлайн';
        }
    } catch {
        document.getElementById('statStatus').textContent = '🔴 Оффлайн';
    }
}

console.log('🚀 ADMIN BOT PANEL LOADED');
console.log('📌 Для входа используй один из 5 ключей');
