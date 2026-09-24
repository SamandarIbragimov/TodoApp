// Tasklar ro'yxatini /api/tasks/ API orqali boshqarish
const listEl = document.getElementById('task-list');
const countEl = document.getElementById('task-count');
const formEl = document.getElementById('task-form');
const titleEl = document.getElementById('task-title');
const errorEl = document.getElementById('task-error');

async function api(url, options = {}) {
    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.API.csrfToken,
            ...(options.headers || {}),
        },
    });
    if (!response.ok) {
        let message = `Xatolik: ${response.status}`;
        try {
            const data = await response.json();
            message = Object.values(data).flat().join(' ') || message;
        } catch (e) { /* javob JSON emas */ }
        throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
}

function taskUrl(id) {
    return `${window.API.tasks}${id}/`;
}

function showError(message) {
    errorEl.textContent = message;
    errorEl.classList.toggle('hidden', !message);
}

function renderTask(task) {
    const done = task.status === 'done';

    const row = document.createElement('div');
    row.className = done
        ? 'flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg'
        : 'flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-lg hover:shadow-sm transition';

    const left = document.createElement('div');
    left.className = 'flex items-center gap-3';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = done;
    checkbox.className = done
        ? 'w-5 h-5 text-green-600 rounded focus:ring-green-500'
        : 'w-5 h-5 text-blue-600 rounded focus:ring-blue-500';
    checkbox.addEventListener('change', () => toggleTask(task, checkbox.checked));

    const title = document.createElement('span');
    title.className = done ? 'text-gray-500 line-through font-medium' : 'text-gray-800 font-medium';
    title.textContent = task.title;

    left.append(checkbox, title);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'text-red-500 hover:text-red-700 text-sm font-medium transition';
    deleteBtn.textContent = "O'chirish";
    deleteBtn.addEventListener('click', () => deleteTask(task));

    row.append(left, deleteBtn);
    return row;
}

async function loadTasks() {
    try {
        const tasks = await api(window.API.tasks);
        listEl.replaceChildren();
        if (tasks.length === 0) {
            listEl.innerHTML = '<p class="text-gray-400 text-center">Hozircha vazifalar yo\'q</p>';
        } else {
            tasks.forEach((task) => listEl.appendChild(renderTask(task)));
        }
        countEl.textContent = `Jami: ${tasks.length} ta`;
    } catch (e) {
        listEl.innerHTML = '';
        showError(e.message);
    }
}

async function toggleTask(task, checked) {
    try {
        await api(taskUrl(task.id), {
            method: 'PATCH',
            body: JSON.stringify({ status: checked ? 'done' : 'todo' }),
        });
        showError('');
    } catch (e) {
        showError(e.message);
    }
    loadTasks();
}

async function deleteTask(task) {
    if (!confirm(`"${task.title}" vazifasini o'chirasizmi?`)) return;
    try {
        await api(taskUrl(task.id), { method: 'DELETE' });
        showError('');
    } catch (e) {
        showError(e.message);
    }
    loadTasks();
}

formEl.addEventListener('submit', async (event) => {
    event.preventDefault();
    const title = titleEl.value.trim();
    if (!title) return;
    try {
        await api(window.API.tasks, {
            method: 'POST',
            body: JSON.stringify({ title }),
        });
        titleEl.value = '';
        showError('');
        loadTasks();
    } catch (e) {
        showError(e.message);
    }
});

loadTasks();
