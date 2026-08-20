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
        if (!response.ok) throw new Error('blacklist.json не найден');
        blacklistData = await response.json();
        renderBlacklist();
    } catch (error) {
        console.error('Ошибка загрузки черного списка:', error);
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
            <div class="entry-admin">👤 Добавил: ${data.added_by || 'Неизвестно'}</
