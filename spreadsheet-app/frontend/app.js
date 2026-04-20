/**
 * Spreadsheet App - Клиентское приложение
 * Веб-редактор таблиц с поддержкой формул
 */

// === Конфигурация ===
const API_BASE = '/api';

// === Состояние приложения ===
const state = {
    token: localStorage.getItem('token'),
    user: null,
    spreadsheets: [],
    currentSpreadsheet: null,
    selectedCell: null,
    cellsData: {}
};

// === DOM элементы ===
const elements = {
    authScreen: document.getElementById('auth-screen'),
    mainScreen: document.getElementById('main-screen'),
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    authError: document.getElementById('auth-error'),
    userInfo: document.getElementById('user-info'),
    logoutBtn: document.getElementById('logout-btn'),
    spreadsheetsPanel: document.getElementById('spreadsheets-panel'),
    editorPanel: document.getElementById('editor-panel'),
    spreadsheetsList: document.getElementById('spreadsheets-list'),
    newSpreadsheetBtn: document.getElementById('new-spreadsheet-btn'),
    backBtn: document.getElementById('back-btn'),
    saveBtn: document.getElementById('save-btn'),
    spreadsheetTitle: document.getElementById('spreadsheet-title'),
    spreadsheet: document.getElementById('spreadsheet'),
    selectedCellDisplay: document.getElementById('selected-cell'),
    formulaInput: document.getElementById('formula-input'),
    modalOverlay: document.getElementById('modal-overlay'),
    newSpreadsheetForm: document.getElementById('new-spreadsheet-form'),
    cancelModalBtn: document.getElementById('cancel-modal-btn')
};

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initForms();
    initEditor();
    initModal();
    
    if (state.token) {
        loadUser();
    }
});

// === Вкладки авторизации ===
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const tab = btn.dataset.tab;
            if (tab === 'login') {
                elements.loginForm.classList.remove('hidden');
                elements.registerForm.classList.add('hidden');
            } else {
                elements.loginForm.classList.add('hidden');
                elements.registerForm.classList.remove('hidden');
            }
        });
    });
}

// === Формы авторизации ===
function initForms() {
    elements.loginForm.addEventListener('submit', handleLogin);
    elements.registerForm.addEventListener('submit', handleRegister);
    elements.logoutBtn.addEventListener('click', handleLogout);
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE}/auth/token`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка входа');
        }
        
        const data = await response.json();
        state.token = data.access_token;
        localStorage.setItem('token', state.token);
        
        showMainScreen();
        loadUser();
        loadSpreadsheets();
    } catch (error) {
        showError(error.message);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    
    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка регистрации');
        }
        
        // Автоматический вход после регистрации
        const loginResponse = await fetch(`${API_BASE}/auth/token`, {
            method: 'POST',
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });
        
        const data = await loginResponse.json();
        state.token = data.access_token;
        localStorage.setItem('token', state.token);
        
        showMainScreen();
        loadUser();
        loadSpreadsheets();
    } catch (error) {
        showError(error.message);
    }
}

function handleLogout() {
    state.token = null;
    state.user = null;
    state.spreadsheets = [];
    state.currentSpreadsheet = null;
    localStorage.removeItem('token');
    showAuthScreen();
}

async function loadUser() {
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Не удалось загрузить данные пользователя');
        }
        
        state.user = await response.json();
        elements.userInfo.textContent = `👤 ${state.user.username}`;
        showMainScreen();
        loadSpreadsheets();
    } catch (error) {
        console.error('Error loading user:', error);
        handleLogout();
    }
}

// === Управление экранами ===
function showAuthScreen() {
    elements.authScreen.classList.remove('hidden');
    elements.mainScreen.classList.add('hidden');
}

function showMainScreen() {
    elements.authScreen.classList.add('hidden');
    elements.mainScreen.classList.remove('hidden');
}

function showSpreadsheetsPanel() {
    elements.spreadsheetsPanel.classList.remove('hidden');
    elements.editorPanel.classList.add('hidden');
}

function showEditorPanel() {
    elements.spreadsheetsPanel.classList.add('hidden');
    elements.editorPanel.classList.remove('hidden');
}

function showError(message) {
    elements.authError.textContent = message;
    elements.authError.classList.remove('hidden');
    setTimeout(() => {
        elements.authError.classList.add('hidden');
    }, 5000);
}

// === Работа с таблицами ===
async function loadSpreadsheets() {
    try {
        const response = await fetch(`${API_BASE}/spreadsheets/`, {
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Не удалось загрузить список таблиц');
        }
        
        state.spreadsheets = await response.json();
        renderSpreadsheetsList();
    } catch (error) {
        console.error('Error loading spreadsheets:', error);
    }
}

function renderSpreadsheetsList() {
    elements.spreadsheetsList.innerHTML = '';
    
    if (state.spreadsheets.length === 0) {
        elements.spreadsheetsList.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 2rem;">Нет созданных таблиц</p>';
        return;
    }
    
    state.spreadsheets.forEach(spreadsheet => {
        const item = document.createElement('div');
        item.className = 'spreadsheet-item';
        item.innerHTML = `
            <div class="spreadsheet-info">
                <h3>${escapeHtml(spreadsheet.name)}</h3>
                <p>${spreadsheet.description || 'Без описания'}</p>
                <p style="font-size: 0.75rem; margin-top: 0.25rem;">Обновлено: ${new Date(spreadsheet.updated_at).toLocaleDateString()}</p>
            </div>
            <div class="spreadsheet-actions">
                <button class="btn-primary open-btn" data-id="${spreadsheet.id}">Открыть</button>
                <button class="btn-danger delete-btn" data-id="${spreadsheet.id}">Удалить</button>
            </div>
        `;
        
        item.querySelector('.open-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            openSpreadsheet(spreadsheet.id);
        });
        
        item.querySelector('.delete-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSpreadsheet(spreadsheet.id);
        });
        
        elements.spreadsheetsList.appendChild(item);
    });
}

async function openSpreadsheet(id) {
    try {
        const response = await fetch(`${API_BASE}/spreadsheets/${id}`, {
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Не удалось открыть таблицу');
        }
        
        state.currentSpreadsheet = await response.json();
        state.cellsData = state.currentSpreadsheet.data?.cells || {};
        
        elements.spreadsheetTitle.textContent = state.currentSpreadsheet.name;
        createSpreadsheetGrid();
        showEditorPanel();
    } catch (error) {
        console.error('Error opening spreadsheet:', error);
        alert('Ошибка при открытии таблицы');
    }
}

async function deleteSpreadsheet(id) {
    if (!confirm('Вы уверены, что хотите удалить эту таблицу?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/spreadsheets/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Не удалось удалить таблицу');
        }
        
        loadSpreadsheets();
    } catch (error) {
        console.error('Error deleting spreadsheet:', error);
        alert('Ошибка при удалении таблицы');
    }
}

async function saveSpreadsheet() {
    if (!state.currentSpreadsheet) return;
    
    try {
        const cells = {};
        document.querySelectorAll('#spreadsheet td[data-cell]').forEach(td => {
            const address = td.dataset.cell;
            const input = td.querySelector('input');
            const value = input.value;
            
            if (value) {
                cells[address] = {
                    value: value,
                    formula: value.startsWith('=') ? value : null
                };
            }
        });
        
        const response = await fetch(`${API_BASE}/spreadsheets/${state.currentSpreadsheet.id}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${state.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: state.currentSpreadsheet.name,
                description: state.currentSpreadsheet.description,
                data: { cells }
            })
        });
        
        if (!response.ok) {
            throw new Error('Не удалось сохранить таблицу');
        }
        
        state.currentSpreadsheet = await response.json();
        alert('Таблица сохранена!');
    } catch (error) {
        console.error('Error saving spreadsheet:', error);
        alert('Ошибка при сохранении таблицы');
    }
}

// === Создание сетки таблицы ===
function createSpreadsheetGrid() {
    const rows = 26;
    const cols = 10;
    
    let html = '<thead><tr><th></th>';
    for (let c = 0; c < cols; c++) {
        html += `<th>${String.fromCharCode(65 + c)}</th>`;
    }
    html += '</tr></thead><tbody>';
    
    for (let r = 1; r <= rows; r++) {
        html += `<tr><td class="row-header">${r}</td>`;
        for (let c = 0; c < cols; c++) {
            const cellAddress = `${String.fromCharCode(65 + c)}${r}`;
            const cellData = state.cellsData[cellAddress];
            const value = cellData ? (cellData.value || '') : '';
            
            html += `<td data-cell="${cellAddress}" class="${cellData && cellData.formula ? 'has-formula' : ''}">`;
            html += `<input type="text" value="${escapeHtml(value)}" data-formula="${cellData && cellData.formula ? escapeHtml(cellData.formula) : ''}">`;
            html += '</td>';
        }
        html += '</tr>';
    }
    html += '</tbody>';
    
    elements.spreadsheet.innerHTML = html;
    attachCellListeners();
}

function attachCellListeners() {
    const inputs = document.querySelectorAll('#spreadsheet td input');
    
    inputs.forEach(input => {
        input.addEventListener('focus', handleCellFocus);
        input.addEventListener('blur', handleCellBlur);
        input.addEventListener('keydown', handleCellKeydown);
        input.addEventListener('input', handleCellInput);
    });
}

function handleCellFocus(e) {
    const td = e.target.closest('td');
    state.selectedCell = td.dataset.cell;
    
    document.querySelectorAll('#spreadsheet td').forEach(cell => {
        cell.classList.remove('selected');
    });
    td.classList.add('selected');
    
    elements.selectedCellDisplay.textContent = state.selectedCell;
    
    const formula = e.target.dataset.formula || e.target.value;
    elements.formulaInput.value = formula;
}

function handleCellBlur(e) {
    // Вычисление формулы при потере фокуса
    const value = e.target.value;
    if (value && value.startsWith('=')) {
        const result = evaluateFormula(value);
        e.target.dataset.formula = value;
        e.target.value = result;
        e.target.closest('td').classList.add('has-formula');
    }
}

function handleCellKeydown(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        e.target.blur();
        
        // Переход к следующей ячейке
        const td = e.target.closest('td');
        const nextTd = td.parentElement.nextElementSibling?.querySelector('td[data-cell]');
        if (nextTd) {
            nextTd.querySelector('input').focus();
        }
    } else if (e.key === 'Tab') {
        // Стандартное поведение Tab
    } else if (e.key === 'Escape') {
        e.target.blur();
    }
}

function handleCellInput(e) {
    const formula = e.target.dataset.formula;
    if (formula && !e.target.value.startsWith('=')) {
        e.target.closest('td').classList.remove('has-formula');
        delete e.target.dataset.formula;
    }
}

// === Обработка формул ===
function evaluateFormula(formula) {
    if (!formula || !formula.startsWith('=')) {
        return formula;
    }
    
    const expression = formula.substring(1).toUpperCase();
    
    try {
        // Поддержка базовых функций
        const result = parseFormula(expression);
        return formatResult(result);
    } catch (error) {
        return '#ERROR!';
    }
}

function parseFormula(expression) {
    // SUM(A1:A5)
    const sumMatch = expression.match(/SUM\(([A-Z])(\d+):([A-Z])(\d+)\)/);
    if (sumMatch) {
        return calculateRange(sumMatch, 'sum');
    }
    
    // AVG(A1:A5)
    const avgMatch = expression.match(/AVG\(([A-Z])(\d+):([A-Z])(\d+)\)/);
    if (avgMatch) {
        return calculateRange(avgMatch, 'avg');
    }
    
    // MIN(A1:A5)
    const minMatch = expression.match(/MIN\(([A-Z])(\d+):([A-Z])(\d+)\)/);
    if (minMatch) {
        return calculateRange(minMatch, 'min');
    }
    
    // MAX(A1:A5)
    const maxMatch = expression.match(/MAX\(([A-Z])(\d+):([A-Z])(\d+)\)/);
    if (maxMatch) {
        return calculateRange(maxMatch, 'max');
    }
    
    // COUNT(A1:A5)
    const countMatch = expression.match(/COUNT\(([A-Z])(\d+):([A-Z])(\d+)\)/);
    if (countMatch) {
        return calculateRange(countMatch, 'count');
    }
    
    // IF(condition, true_value, false_value)
    const ifMatch = expression.match(/IF\(([^,]+),([^,]+),(.+)\)/);
    if (ifMatch) {
        const condition = evaluateCondition(ifMatch[1].trim());
        return condition ? parseSimpleExpression(ifMatch[2].trim()) : parseSimpleExpression(ifMatch[3].trim());
    }
    
    // Простые арифметические выражения
    return parseSimpleExpression(expression);
}

function calculateRange(match, operation) {
    const [, startCol, startRow, endCol, endRow] = match;
    const values = [];
    
    const startC = startCol.charCodeAt(0);
    const endC = endCol.charCodeAt(0);
    const startR = parseInt(startRow);
    const endR = parseInt(endRow);
    
    for (let c = startC; c <= endC; c++) {
        for (let r = startR; r <= endR; r++) {
            const cellAddress = `${String.fromCharCode(c)}${r}`;
            const input = document.querySelector(`#spreadsheet td[data-cell="${cellAddress}"] input`);
            if (input) {
                const value = parseFloat(input.value) || 0;
                values.push(value);
            }
        }
    }
    
    switch (operation) {
        case 'sum':
            return values.reduce((a, b) => a + b, 0);
        case 'avg':
            return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
        case 'min':
            return Math.min(...values);
        case 'max':
            return Math.max(...values);
        case 'count':
            return values.length;
        default:
            return 0;
    }
}

function evaluateCondition(condition) {
    // Поддержка простых условий: A1>5, B2=10, C3<100
    const operators = ['>=', '<=', '<>', '!=', '=', '>', '<'];
    
    for (const op of operators) {
        const parts = condition.split(op);
        if (parts.length === 2) {
            const left = getCellValue(parts[0].trim());
            const right = parseFloat(parts[1].trim()) || parts[1].trim().replace(/['"]/g, '');
            
            switch (op) {
                case '>=': return left >= right;
                case '<=': return left <= right;
                case '<>':
                case '!=': return left !== right;
                case '=': return left == right;
                case '>': return left > right;
                case '<': return left < right;
            }
        }
    }
    
    return !!condition;
}

function getCellValue(cellRef) {
    const match = cellRef.match(/^([A-Z]+)(\d+)$/);
    if (match) {
        const input = document.querySelector(`#spreadsheet td[data-cell="${cellRef}"] input`);
        if (input) {
            return parseFloat(input.value) || input.value;
        }
    }
    return parseFloat(cellRef) || cellRef;
}

function parseSimpleExpression(expr) {
    // Замена ссылок на ячейки их значениями
    expr = expr.replace(/([A-Z]+\d+)/g, (match) => {
        return getCellValue(match);
    });
    
    // Безопасное вычисление
    try {
        // Разрешаем только цифры, операторы и скобки
        if (/^[\d+\-*/().\s]+$/.test(expr)) {
            return Function('"use strict";return (' + expr + ')')();
        }
        return expr;
    } catch {
        return expr;
    }
}

function formatResult(result) {
    if (typeof result === 'number') {
        return Number.isInteger(result) ? result.toString() : result.toFixed(2);
    }
    return String(result);
}

// === Formula bar ===
elements.formulaInput.addEventListener('input', () => {
    if (state.selectedCell) {
        const input = document.querySelector(`#spreadsheet td[data-cell="${state.selectedCell}"] input`);
        if (input) {
            input.value = elements.formulaInput.value;
        }
    }
});

elements.formulaInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        if (state.selectedCell) {
            const input = document.querySelector(`#spreadsheet td[data-cell="${state.selectedCell}"] input`);
            if (input) {
                input.focus();
                input.blur();
            }
        }
    }
});

// === Модальное окно ===
function initModal() {
    elements.newSpreadsheetBtn.addEventListener('click', () => {
        elements.modalOverlay.classList.remove('hidden');
    });
    
    elements.cancelModalBtn.addEventListener('click', () => {
        elements.modalOverlay.classList.add('hidden');
        elements.newSpreadsheetForm.reset();
    });
    
    elements.modalOverlay.addEventListener('click', (e) => {
        if (e.target === elements.modalOverlay) {
            elements.modalOverlay.classList.add('hidden');
            elements.newSpreadsheetForm.reset();
        }
    });
    
    elements.newSpreadsheetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const name = document.getElementById('spreadsheet-name').value;
        const description = document.getElementById('spreadsheet-description').value;
        
        try {
            const response = await fetch(`${API_BASE}/spreadsheets/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${state.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name, description })
            });
            
            if (!response.ok) {
                throw new Error('Не удалось создать таблицу');
            }
            
            elements.modalOverlay.classList.add('hidden');
            elements.newSpreadsheetForm.reset();
            loadSpreadsheets();
        } catch (error) {
            console.error('Error creating spreadsheet:', error);
            alert('Ошибка при создании таблицы');
        }
    });
}

// === Кнопки навигации ===
elements.backBtn.addEventListener('click', () => {
    state.currentSpreadsheet = null;
    state.cellsData = {};
    showSpreadsheetsPanel();
});

elements.saveBtn.addEventListener('click', saveSpreadsheet);

// === Инициализация редактора ===
function initEditor() {
    // Дополнительные обработчики для редактора
}

// === Утилиты ===
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
