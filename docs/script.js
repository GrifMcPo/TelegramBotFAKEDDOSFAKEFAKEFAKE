const VALID_KEYS = [
    'OWNER!KEY!_%!$W@$%OWENR!@#W$!($',
    'ADMIN!KEY!@#$%^&*()',
    'SUPER!ADMIN!KEY!12345',
    'BOSS!KEY!_!@#$%^&*',
    'MASTER!KEY!QWERTY123'
];

const DATA_URL = 'https://raw.githubusercontent.com/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/main/';
const API_URL = 'https://api.github.com/repos/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/contents/';

let logsData = [];
let blacklistData = {};

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
        loadAllData();
        setInterval(loadAllData, 30000);
        startClock();
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

// ========== ЧАСЫ ==========
function startClock() {
    setInterval(() => {
        const now = new Date();
        const time = now.toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow' });
        document.getElementById('liveTime').textContent = `🕐 ${time} МСК`;
    }, 1000);
}

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
    await loadLogs();
    await loadBlacklist();
}

async function loadLogs() {
    try {
        const response = await fetch(DATA_URL + 'logs.json?t=' + Date.now());
        if (!response.ok) throw new Error('logs.json не найден');
        logsData = await response.json();
        renderLogs();
        renderChats();
        renderStats();
        document.getElementById('updateTime').textContent = '🔄 Обновлено: ' + new Date().toLocaleTimeString('ru-RU');
    } catch (error) {
        console.error('Ошибка:', error);
        document.getElementById('logsContainer').innerHTML = '<div class="loading-text">❌ Ошибка загрузки данных</div>';
        showDemoData();
    }
}

async function loadBlacklist() {
    try {
        const response = await fetch(DATA_URL + 'blacklist.json?t=' + Date.now());
        if (!response.ok) {
            console.warn('⚠️ blacklist.json не найден');
            blacklistData = {};
            renderBlacklist();
            return;
        }
        blacklistData = await response.json();
        renderBlacklist();
    } catch (error) {
        console.warn('⚠️ Ошибка загрузки черного списка:', error);
        blacklistData = {};
        renderBlacklist();
    }
}

function renderBlacklist() {
    const container = document.getElementById('blacklistContainer');
    const entries = Object.entries(blacklistData);

    if (!entries.length) {
        container.innerHTML = '<div class="loading-text">📭 Черный список пуст</div>';
        return;
    }

    container.innerHTML = entries.map(([userId, data]) => `
        <div class="blacklist-entry">
            <div class="entry-header">
                <span class="entry-id">🆔 ${userId}</span>
                <span class="entry-time">${data.added_at || 'Неизвестно'}</span>
            </div>
            <div class="entry-reason">📌 ${data.reason || 'Причина не указана'}</div>
            <div class="entry-admin">👤 Добавил: ${data.added_by || 'Неизвестно'}</div>
        </div>
    `).join('');
}

function showDemoData() {
    logsData = [
        { "command": "/start", "username": "SlNpidora", "user_id": "8308522569", "time": "20.08.2026 15:30:00",
            "type": "command" },
        { "command": "/whois ip 8.8.8.8", "username": "SlNpidora", "user_id": "8308522569", "target": "8.8.8.8",
            "time": "20.08.2026 15:31:00", "type": "probe" },
    ];
    renderLogs();
    renderChats();
    renderStats();
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
            <div class="log-type">${log.type || 'command'}</div>
        </div>
    `).join('');
}

function renderChats() {
    const container = document.getElementById('chatsContainer');
    const users = {};

    logsData.forEach(log => {
        const id = log.user_id;
        if (!users[id]) users[id] = { username: log.username || 'Нет', count: 0, logs: [] };
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
            <div class="chat-last">🕐 ${data.logs[data.logs.length - 1]?.time || 'Нет'}</div>
        </div>
    `).join('');
}

function renderStats() {
    const users = new Set(logsData.map(l => l.user_id));
    const probes = logsData.filter(l => l.type === 'probe');
    document.getElementById('statUsers').textContent = users.size;
    document.getElementById('statCommands').textContent = logsData.length;
    document.getElementById('statProbes').textContent = probes.length;
    document.getElementById('statLastUpdate').textContent = new Date().toLocaleTimeString('ru-RU');
}

function filterLogs() { renderLogs(); }

// ========== МОДАЛКА ==========
function openChat(userId, username, logs) {
    let modal = document.getElementById('chatModal');
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
        modal = document.getElementById('chatModal');
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

    modal.classList.add('active');
}

function closeChat() {
    const modal = document.getElementById('chatModal');
    if (modal) modal.classList.remove('active');
}

// ========== АЛИАС ДЛЯ КНОПКИ ОБНОВЛЕНИЯ ==========
function loadData() {
    loadAllData();
}

// ========== ЧЕРНЫЙ СПИСОК (ДОБАВЛЕНИЕ/УДАЛЕНИЕ) ==========
document.getElementById('blockBtn').addEventListener('click', async function() {
    const userId = document.getElementById('blockUserId').value.trim();
    const reason = document.getElementById('blockReason').value.trim();
    const messageDiv = document.getElementById('blockMessage');

    if (!userId) {
        messageDiv.textContent = '❌ Введите ID пользователя!';
        messageDiv.className = 'message error';
        return;
    }

    if (!reason) {
        messageDiv.textContent = '❌ Введите причину блокировки!';
        messageDiv.className = 'message error';
        return;
    }

    try {
        const response = await fetch(API_URL + 'blacklist.json', {
            method: 'GET',
            headers: { 'Accept': 'application/vnd.github.v3+json' }
        });

        let sha = null;
        let content = {};

        if (response.status === 200) {
            const data = await response.json();
            sha = data.sha;
            content = JSON.parse(atob(data.content));
        }

        content[userId] = {
            reason: reason,
            added_by: 'Админ (сайт)',
            added_at: new Date().toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' })
        };

        const encoded = btoa(JSON.stringify(content, null, 2));

        const updateResponse = await fetch(API_URL + 'blacklist.json', {
            method: 'PUT',
            headers: {
                'Authorization': 'token ghp_...', // Тут нужен токен
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: `⛔ Добавлен в черный список: ${userId}`,
                content: encoded,
                sha: sha,
                branch: 'main'
            })
        });

        if (updateResponse.status === 200 || updateResponse.status === 201) {
            messageDiv.textContent = `✅ Пользователь ${userId} добавлен в черный список!`;
            messageDiv.className = 'message success';
            document.getElementById('blockUserId').value = '';
            document.getElementById('blockReason').value = '';
            await loadBlacklist();
        } else {
            const error = await updateResponse.json();
            messageDiv.textContent = `❌ Ошибка: ${error.message || 'Неизвестная ошибка'}`;
            messageDiv.className = 'message error';
        }
    } catch (error) {
        messageDiv.textContent = `❌ Ошибка: ${error.message}`;
        messageDiv.className = 'message error';
    }
});

document.getElementById('unblockBtn').addEventListener('click', async function() {
    const userId = document.getElementById('unblockUserId').value.trim();
    const messageDiv = document.getElementById('unblockMessage');

    if (!userId) {
        messageDiv.textContent = '❌ Введите ID пользователя!';
        messageDiv.className = 'message error';
        return;
    }

    try {
        const response = await fetch(API_URL + 'blacklist.json', {
            method: 'GET',
            headers: { 'Accept': 'application/vnd.github.v3+json' }
        });

        let sha = null;
        let content = {};

        if (response.status === 200) {
            const data = await response.json();
            sha = data.sha;
            content = JSON.parse(atob(data.content));
        }

        if (!content[userId]) {
            messageDiv.textContent = `❌ Пользователь ${userId} не найден в черном списке!`;
            messageDiv.className = 'message error';
            return;
        }

        delete content[userId];
        const encoded = btoa(JSON.stringify(content, null, 2));

        const updateResponse = await fetch(API_URL + 'blacklist.json', {
            method: 'PUT',
            headers: {
                'Authorization': 'token ghp_...', // Тут нужен токен
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: `✅ Удален из черного списка: ${userId}`,
                content: encoded,
                sha: sha,
                branch: 'main'
            })
        });

        if (updateResponse.status === 200 || updateResponse.status === 201) {
            messageDiv.textContent = `✅ Пользователь ${userId} удален из черного списка!`;
            messageDiv.className = 'message success';
            document.getElementById('unblockUserId').value = '';
            await loadBlacklist();
        } else {
            const error = await updateResponse.json();
            messageDiv.textContent = `❌ Ошибка: ${error.message || 'Неизвестная ошибка'}`;
            messageDiv.className = 'message error';
        }
    } catch (error) {
        messageDiv.textContent = `❌ Ошибка: ${error.message}`;
        messageDiv.className = 'message error';
    }
});

console.log('🚀 ADMIN PANEL LOADED');
