/* ==========================================================================
   TaskFlow Flask Todo App - Frontend JavaScript Logic
   ========================================================================== */

let currentStatusFilter = '';
let searchDebounceTimer = null;

// DOM Load Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Set Today's Date in Header
    const today = new Date();
    const dateStr = today.getFullYear() + '.' + String(today.getMonth() + 1).padStart(2, '0') + '.' + String(today.getDate()).padStart(2, '0');
    document.getElementById('today-date').textContent = dateStr;

    // Set Default Due Date in Form to Today
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    document.getElementById('form-duedate').value = `${yyyy}-${mm}-${dd}`;

    // Load Initial Data
    loadTodos();
    loadStats();
});

// Fetch & Render Todos
async function loadTodos() {
    const search = document.getElementById('search-input').value.trim();
    const category = document.getElementById('category-filter').value;
    const priority = document.getElementById('priority-filter').value;

    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (category) params.append('category', category);
    if (priority) params.append('priority', priority);
    if (currentStatusFilter) params.append('status', currentStatusFilter);

    try {
        const response = await fetch(`/api/todos?${params.toString()}`);
        if (!response.ok) throw new Error('Failed to fetch todo list');
        const todos = await response.json();
        renderTodos(todos);
    } catch (err) {
        console.error(err);
        showToast('할일 목록을 불러오는 중 오류가 발생했습니다.', 'danger');
    }
}

// Fetch & Update Stats Dashboard
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Failed to fetch stats');
        const stats = await response.json();

        document.getElementById('stat-total').textContent = stats.total;
        document.getElementById('stat-completed').textContent = stats.completed;
        document.getElementById('stat-urgent').textContent = stats.high_priority;
        
        const percent = stats.completion_rate || 0;
        document.getElementById('stat-percent').textContent = `${percent}%`;
        document.getElementById('progress-fill').style.width = `${percent}%`;
    } catch (err) {
        console.error(err);
    }
}

// Render Todo Items
function renderTodos(todos) {
    const container = document.getElementById('todo-list');
    const emptyState = document.getElementById('empty-state');

    container.innerHTML = '';

    if (!todos || todos.length === 0) {
        emptyState.style.display = 'flex';
        return;
    }

    emptyState.style.display = 'none';

    todos.forEach(todo => {
        const card = document.createElement('div');
        card.className = `todo-card ${todo.is_completed ? 'completed' : ''}`;
        card.id = `todo-${todo.id}`;

        // Category Badge Info
        const catMap = {
            'Work': { label: '💼 업무', class: 'badge-cat-work' },
            'Personal': { label: '🏡 개인', class: 'badge-cat-personal' },
            'Shopping': { label: '🛒 쇼핑', class: 'badge-cat-shopping' },
            'Health': { label: '💪 건강', class: 'badge-cat-health' },
            'Study': { label: '📚 학습', class: 'badge-cat-study' },
            'Other': { label: '📌 기타', class: 'badge-cat-other' }
        };
        const catInfo = catMap[todo.category] || { label: todo.category, class: 'badge-cat-other' };

        // Priority Badge Info
        const prioMap = {
            'High': { label: '🔴 높은 우선순위', class: 'badge-priority-high' },
            'Medium': { label: '🟡 보통', class: 'badge-priority-medium' },
            'Low': { label: '🟢 낮음', class: 'badge-priority-low' }
        };
        const prioInfo = prioMap[todo.priority] || { label: todo.priority, class: 'badge-priority-medium' };

        // Due Date Format & Alert
        let dueDateHtml = '';
        if (todo.due_date) {
            const todayStr = new Date().toISOString().split('T')[0];
            let dueClass = 'due-badge';
            let icon = 'fa-regular fa-clock';
            
            if (!todo.is_completed) {
                if (todo.due_date < todayStr) {
                    dueClass += ' overdue';
                    icon = 'fa-solid fa-triangle-exclamation';
                } else if (todo.due_date === todayStr) {
                    dueClass += ' today';
                    icon = 'fa-solid fa-calendar-day';
                }
            }

            dueDateHtml = `
                <div class="${dueClass}">
                    <i class="${icon}"></i> ${todo.due_date}
                </div>
            `;
        }

        card.innerHTML = `
            <div class="todo-checkbox-wrapper">
                <div class="custom-checkbox" onclick="toggleTodo(${todo.id})">
                    <i class="fa-solid fa-check"></i>
                </div>
            </div>
            <div class="todo-content">
                <div class="todo-header-row">
                    <span class="todo-title">${escapeHtml(todo.title)}</span>
                    <span class="badge ${catInfo.class}">${catInfo.label}</span>
                    <span class="badge ${prioInfo.class}">${prioInfo.label}</span>
                </div>
                ${todo.description ? `<p class="todo-desc">${escapeHtml(todo.description)}</p>` : ''}
                <div class="todo-footer">
                    ${dueDateHtml}
                </div>
            </div>
            <div class="todo-actions">
                <button class="icon-btn" onclick="openEditModal(${todo.id})" title="수정">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button class="icon-btn btn-delete" onclick="deleteTodo(${todo.id})" title="삭제">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </div>
        `;

        container.appendChild(card);
    });
}

// Toggle Todo Completion
async function toggleTodo(id) {
    try {
        const response = await fetch(`/api/todos/${id}/toggle`, { method: 'PATCH' });
        if (!response.ok) throw new Error('Toggle failed');
        const updated = await response.json();
        
        loadTodos();
        loadStats();

        const msg = updated.is_completed ? '할일을 완료 처리했습니다! 🎉' : '진행 중으로 변경했습니다.';
        showToast(msg, 'success');
    } catch (err) {
        console.error(err);
        showToast('상태 변경에 실패했습니다.', 'danger');
    }
}

// Handle Form Submission (Add or Edit)
async function handleFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('todo-id').value;
    const title = document.getElementById('form-title').value.trim();
    const description = document.getElementById('form-description').value.trim();
    const category = document.getElementById('form-category').value;
    const priority = document.getElementById('form-priority').value;
    const due_date = document.getElementById('form-duedate').value;

    if (!title) {
        showToast('제목을 입력해주세요.', 'danger');
        return;
    }

    const payload = { title, description, category, priority, due_date };
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/todos/${id}` : '/api/todos';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Save failed');

        closeModal();
        loadTodos();
        loadStats();

        showToast(id ? '할일이 수정되었습니다.' : '새 할일이 추가되었습니다!', 'success');
    } catch (err) {
        console.error(err);
        showToast('저장 중 오류가 발생했습니다.', 'danger');
    }
}

// Open Add Modal
function openAddModal() {
    document.getElementById('todo-id').value = '';
    document.getElementById('modal-title').innerHTML = '<i class="fa-solid fa-plus-circle"></i> 새 할일 등록';
    document.getElementById('todo-form').reset();

    const todayStr = new Date().toISOString().split('T')[0];
    document.getElementById('form-duedate').value = todayStr;

    document.getElementById('todo-modal').classList.add('active');
}

// Open Edit Modal
async function openEditModal(id) {
    try {
        const response = await fetch(`/api/todos/${id}`);
        if (!response.ok) throw new Error('Fetch todo details failed');
        const todo = await response.json();

        document.getElementById('todo-id').value = todo.id;
        document.getElementById('modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square"></i> 할일 수정';
        document.getElementById('form-title').value = todo.title;
        document.getElementById('form-description').value = todo.description || '';
        document.getElementById('form-category').value = todo.category || 'Work';
        document.getElementById('form-priority').value = todo.priority || 'Medium';
        document.getElementById('form-duedate').value = todo.due_date || '';

        document.getElementById('todo-modal').classList.add('active');
    } catch (err) {
        console.error(err);
        showToast('상세 정보를 불러올 수 없습니다.', 'danger');
    }
}

// Close Modal
function closeModal() {
    document.getElementById('todo-modal').classList.remove('active');
}

// Delete Todo
async function deleteTodo(id) {
    if (!confirm('정말 이 할일을 삭제하시겠습니까?')) return;

    try {
        const response = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Delete failed');

        loadTodos();
        loadStats();
        showToast('할일이 삭제되었습니다.', 'info');
    } catch (err) {
        console.error(err);
        showToast('삭제 실패했습니다.', 'danger');
    }
}

// Clear All Completed Todos
async function clearCompleted() {
    if (!confirm('완료된 모든 항목을 삭제하시겠습니까?')) return;

    try {
        const response = await fetch('/api/todos/completed', { method: 'DELETE' });
        if (!response.ok) throw new Error('Clear completed failed');
        const result = await response.json();

        loadTodos();
        loadStats();
        showToast(`${result.deleted_count}개의 완료된 항목을 삭제했습니다.`, 'info');
    } catch (err) {
        console.error(err);
        showToast('완료 항목 삭제에 실패했습니다.', 'danger');
    }
}

// Filter Control Handlers
function setStatusFilter(status, btnElement) {
    currentStatusFilter = status;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    btnElement.classList.add('active');
    loadTodos();
}

function applyFilters() {
    loadTodos();
}

function debounceSearch() {
    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('clear-search-btn');
    clearBtn.style.display = input.value ? 'block' : 'none';

    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        loadTodos();
    }, 300);
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('clear-search-btn').style.display = 'none';
    loadTodos();
}

// Toast System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    if (type === 'danger') iconClass = 'fa-solid fa-circle-exclamation';

    toast.innerHTML = `<i class="${iconClass}"></i> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Utility: HTML Escape
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
