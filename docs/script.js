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
        loadData();
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
function loadData() {
    // Статистика (заглушка)
    document.getElementById('statUsers').textContent = '42';
    document.getElementById('statCommands').textContent = '1,337';
    document.getElementById('statUptime').textContent = '2ч 17м';
    document.getElementById('statStatus').textContent = '✅';

    // Пользователи (заглушка)
    const users = [
        { id: '8308522569', username: 'SlNpidora', connected: '18.08.2026 22:43' },
        { id: '8857252828', username: 'GrifMcPo', connected: '18.08.2026 22:45' },
    ];

    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = users.map((u, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${u.id}</td>
            <td>@${u.username}</td>
            <td>${u.connected}</td>
        </tr>
    `).join('');
}

// ============================================================
// КНОПКИ ДЛЯ ДЕМОНСТРАЦИИ
// ============================================================
document.querySelectorAll('.stat-card').forEach(card => {
    card.addEventListener('click', () => {
        // Просто анимация для красоты
        card.style.transition = 'all 0.2s';
        card.style.transform = 'scale(0.95)';
        setTimeout(() => card.style.transform = 'scale(1)', 200);
    });
});
