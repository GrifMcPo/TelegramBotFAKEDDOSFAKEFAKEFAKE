const VALID_KEYS = [
    'OWNER!KEY!_%!$W@$%OWENR!@#W$!($',
    'ADMIN!KEY!@#$%^&*()',
    'SUPER!ADMIN!KEY!12345',
    'BOSS!KEY!_!@#$%^&*',
    'MASTER!KEY!QWERTY123'
];

const DATA_URL = 'https://raw.githubusercontent.com/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/main/';

const loginPage = document.getElementById('loginPage');
const mainPage = document.getElementById('mainPage');
const keyInput = document.getElementById('keyInput');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');
const logoutBtn = document.getElementById('logoutBtn');

// ========== ВХОД ==========
function login() {
    const key = keyInput.value.trim();
    if (VALID_KEYS.includes(key)) {
        loginPage.style.display = 'none';
        mainPage.style.display = 'block';
        loginError.classList.remove('show');
        loadAllData();
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

// ========== ТАБЫ ==========
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const tab = btn.dataset.tab;
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`tab-${tab}`).classList.add('active');
    });
});

// ========== ЗАГРУЗКА ==========
async function loadAllData() {
    await Promise.all([loadUsers(), loadStats(), loadChats()]);
}

async function loadUsers() {
    try {
        const response = await fetch(DATA_URL + 'users.json?t=' + Date.now());
        if (!response.ok) throw new Error('users.json не найден');
        const data = await response.json();
        
        const userIds = Object.keys(data);
        document.getElementById('statUsers').textContent = userIds.length;
        
        const tbody = document.getElementById('usersTableBody');
        if (userIds.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Нет пользователей</td></tr>';
            return;
        }
        
        tbody.innerHTML = userIds.map((id, i) => {
            const user = data[id];
            return `<tr><td>${i+1}</td><td>${id}</td><td>@${user.username || 'Нет'}</td><td>${user.connected_at || 'Неизвестно'}</td></tr>`;
        }).join('');
        
        document.getElementById('statUptime').textContent = new Date().toLocaleTimeString('ru-RU');
    } catch (error) {
        console.error('❌ Ошибка:', error);
        document.getElementById('usersTableBody').innerHTML = '<tr><td colspan="4" class="loading-text">❌ Ошибка</td></tr>';
    }
}

async function loadStats() {
    try {
        const response = await fetch(DATA_URL + 'stats.json?t=' + Date.now());
        if (!response.ok) throw new Error('stats.json не найден');
        const data = await response.json();
        document.getElementById('statCommands').textContent = data.total_commands || 0;
        document.getElementById('statStatus').textContent = data.total_connections > 0 ? '🟢 Онлайн' : '🔴 Оффлайн';
    } catch (error) {
        console.error('❌ Ошибка:', error);
    }
}

async function loadChats() {
    try {
        const response = await fetch(DATA_URL + 'users.json?t=' + Date.now());
        if (!response.ok) throw new Error('users.json не найден');
        const data = await response.json();
        
        const container = document.getElementById('chatsContainer');
        const userIds = Object.keys(data);
        
        if (userIds.length === 0) {
            container.innerHTML = '<div class="loading-text">Нет чатов</div>';
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
        console.error('❌ Ошибка:', error);
        document.getElementById('chatsContainer').innerHTML = '<div class="loading-text">❌ Ошибка загрузки</div>';
    }
}

function showChatInfo(chatId) {
    alert(`📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n🆔 ID: ${chatId}\n📌 Команды будут отображаться здесь\n🕐 Время: ${new Date().toLocaleString('ru-RU')}`);
}

setInterval(loadAllData, 15000);
