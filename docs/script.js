const VALID_KEYS = ['OWNER!KEY!_%!$W@$%OWENR!@#W$!($', 'ADMIN!KEY!@#$%^&*()', 'SUPER!ADMIN!KEY!12345', 'BOSS!KEY!_!@#$%^&*', 'MASTER!KEY!QWERTY123'];
const DATA_URL = 'https://raw.githubusercontent.com/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/main/';

let logsData = [];

// ========== ВХОД ==========
const loginPage = document.getElementById('loginPage');
const mainPage = document.getElementById('mainPage');
const keyInput = document.getElementById('keyInput');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');
const logoutBtn = document.getElementById('logoutBtn');

function login() {
    const key = keyInput.value.trim();
    if (VALID_KEYS.includes(key)) {
        loginPage.style.display = 'none';
        mainPage.style.display = 'block';
        loginError.classList.remove('show');
        loadData();
        setInterval(loadData, 15000);
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
async function loadData() {
    try {
        const response = await fetch(DATA_URL + 'logs.json?t=' + Date.now());
        if (!response.ok) throw new Error('logs.json не найден');
        logsData = await response.json();
        renderLogs();
        renderChats();
        renderStats();
    } catch (error) {
        console.error('Ошибка:', error);
        document.getElementById('logsContainer').innerHTML = '<div class="loading-text">❌ Ошибка загрузки данных</div>';
    }
}

function renderLogs() {
    const container = document.getElementById('logsContainer');
    const search = document.getElementById('searchLogs').value.toLowerCase();
    
    const filtered = logsData.filter(log => 
        (log.command || '').toLowerCase().includes(search) ||
        (log.username || '').toLowerCase().includes(search) ||
        (log.target || '').toLowerCase().includes(search)
    );
    
    if (!filtered.length) {
        container.innerHTML = '<div class="loading-text">📭 Нет записей</div>';
        return;
    }
    
    container.innerHTML = filtered.slice().reverse().map(log => `
        <div class="log-entry">
            <div class="log-header">
                <span class="log-user">👤 ${log.username || 'Нет'} (${log.user_id || '?'})</span>
                <span class="log-time">${log.time || ''}</span>
            </div>
            <div class="log-command">📝 ${log.command || 'Неизвестно'}</div>
            ${log.target ? `<div class="log-target">🎯 ${log.target}</div>` : ''}
        </div>
    `).join('');
}

function renderChats() {
    const container = document.getElementById('chatsContainer');
    const users = {};
    
    logsData.forEach(log => {
        const id = log.user_id;
        if (!users[id]) users[id] = { username: log.username || 'Нет', full_name: log.full_name || 'Нет', count: 0, logs: [] };
        users[id].count++;
        users[id].logs.push(log);
    });
    
    const entries = Object.entries(users);
    if (!entries.length) {
        container.innerHTML = '<div class="loading-text">📭 Нет пользователей</div>';
        return;
    }
    
    container.innerHTML = entries.map(([id, data]) => `
        <div class="chat-card" onclick="openChat('${id}', '${data.username}', ${JSON.stringify(data.logs).replace(/"/g, '&quot;')})">
            <div class="chat-username">👤 ${data.username}</div>
            <div class="chat-id">🆔 ${id}</div>
            <div class="chat-count">📝 ${data.count} команд</div>
            <div class="chat-last">🕐 ${data.logs[data.logs.length-1]?.time || 'Нет'}</div>
        </div>
    `).join('');
}

function renderStats() {
    const users = new Set(logsData.map(l => l.user_id));
    const probes = logsData.filter(l => l.type === 'probe');
    document.getElementById('statUsers').textContent = users.size;
    document.getElementById('statCommands').textContent = logsData.length;
    document.getElementById('statProbes').textContent = probes.length;
    document.getElementById('statTime').textContent = new Date().toLocaleTimeString('ru-RU');
}

function filterLogs() { renderLogs(); }

// ========== ОТКРЫТИЕ ЧАТА ==========
function openChat(userId, username, logs) {
    const modal = document.getElementById('chatModal');
    if (!modal) {
        const newModal = document.createElement('div');
        newModal.id = 'chatModal';
        newModal.className = 'chat-modal';
        newModal.innerHTML = `
            <div class="chat-modal-content">
                <div class="modal-header">
                    <h2 id="modalTitle">💬 Чат с пользователем</h2>
                    <button class="modal-close" onclick="closeChat()">✕</button>
                </div>
                <div id="modalMessages"></div>
            </div>
        `;
        document.body.appendChild(newModal);
    }
    
    document.getElementById('modalTitle').textContent = `💬 @${username} (${userId})`;
    const container = document.getElementById('modalMessages');
    container.innerHTML = logs.slice().reverse().map(log => `
        <div class="modal-message">
            <div class="msg-time">${log.time || ''}</div>
            <div class="msg-command">📝 ${log.command || 'Неизвестно'}</div>
            ${log.target ? `<div class="msg-target">🎯 ${log.target}</div>` : ''}
        </div>
    `).join('');
    
    document.getElementById('chatModal').classList.add('active');
}

function closeChat() {
    document.getElementById('chatModal').classList.remove('active');
}

// ========== ИНИЦИАЛИЗАЦИЯ ==========
console.log('🚀 ADMIN PANEL LOADED');
