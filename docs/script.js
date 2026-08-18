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
// Для GitHub Pages данные берутся из репозитория
// Файлы users.json и stats.json создаются ботом
const DATA_URL = 'https://raw.githubusercontent.com/GrifMcPo/TelegramBotFAKEDDOSFAKEFAKEFAKE/main/';
// ИЛИ если сайт на GitHub Pages:
// const DATA_URL = 'https://grifmcpo.github.io/TelegramBotFAKEDDOSFAKEFAKEFAKE/';

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
    } else {
        loginError.classList.add('show');
        keyInput.value = '';
        keyInput.focus();
        setTimeout(() => loginError.classList.remove('show'), 3000);
    }
}

loginBtn.addEventListener('click', login);
keyInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') login();
});

// ============================================================
// ВЫХОД
// ============================================================
logoutBtn.addEventListener('click', () => {
    mainPage.style.display = 'none';
    loginPage.style.display = 'flex';
    keyInput.value = '';
    keyInput.focus();
});

// ============================================================
// ЗАГРУЗКА ДАННЫХ
// ============================================================
async function loadAllData() {
    await loadUsers();
    await loadStats();
    await loadCommands();
}

async function loadUsers() {
    try {
        const response = await fetch(DATA_URL + 'users.json?t=' + Date.now());
        if (!response.ok) throw new Error('Файл users.json не найден');
        const data = await response.json();
        
        const userIds = Object.keys(data);
        document.getElementById('statUsers').textContent = userIds.length;
        
        const tbody = document.getElementById('usersTableBody');
        if (userIds.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Нет подключенных пользователей</td></tr>';
            return;
        }
        
        tbody.innerHTML = userIds.map((id, i) => {
            const user = data[id];
            return `
                <tr>
                    <td>${i + 1}</td>
                    <td>${id}</td>
                    <td>@${user.username || 'Нет'}</td>
                    <td>${user.connected_at || 'Неизвестно'}</td>
                </tr>
            `;
        }).join('');
        
        // Обновляем время последнего обновления
        document.getElementById('statUptime').textContent = new Date().toLocaleTimeString('ru-RU');
        
    } catch (error) {
        console.error('❌ Ошибка загрузки users.json:', error);
        document.getElementById('usersTableBody').innerHTML = '<tr><td colspan="4" class="loading-text">❌ Ошибка загрузки данных</td></tr>';
    }
}

async function loadStats() {
    try {
        const response = await fetch(DATA_URL + 'stats.json?t=' + Date.now());
        if (!response.ok) throw new Error('Файл stats.json не найден');
        const data = await response.json();
        
        document.getElementById('statCommands').textContent = data.total_commands || 0;
        document.getElementById('statStatus').textContent = data.total_connections > 0 ? '🟢 Онлайн' : '🔴 Оффлайн';
        
    } catch (error) {
        console.error('❌ Ошибка загрузки stats.json:', error);
    }
}

async function loadCommands() {
    // Команды уже есть в HTML, просто обновляем время
    const now = new Date().toLocaleString('ru-RU', { timeZone: 'Europe/Moscow' });
    document.querySelector('.footer-small').textContent = `🕐 Данные обновлены: ${now} (МСК)`;
}

// ============================================================
// АВТООБНОВЛЕНИЕ (КАЖДЫЕ 30 СЕКУНД)
// ============================================================
setInterval(loadAllData, 30000);

// ============================================================
// ЭФФЕКТЫ
// ============================================================
document.querySelectorAll('.stat-card').forEach(card => {
    card.addEventListener('click', () => {
        card.style.transition = 'all 0.2s';
        card.style.transform = 'scale(0.95)';
        setTimeout(() => card.style.transform = 'scale(1)', 200);
    });
});
