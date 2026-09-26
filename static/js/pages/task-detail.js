import * as api from '../api.js';
import { initApp } from '../app.js';
import { openTaskForm } from '../components/task-form.js';
import {
    $, avatar, clear, confirmDialog, currentUser, dueBadge, el, emptyState, formatDateTime,
    icon, PRIORITY, priorityPill, select, showError, STATUS, tagChip, toast, withLoading,
} from '../ui.js';

const taskId = JSON.parse($('#task-id').textContent);
let task = null;
let projects = [];
let myRole = null; // loyihadagi rolim (izohlarni o'chirish huquqi uchun)

function renderActions() {
    clear($('#task-actions'),
        task.can_edit && el('button', { class: 'btn', type: 'button', onclick: edit }, icon('edit'), 'Tahrirlash'),
        task.can_delete && el('button', { class: 'btn btn-danger', type: 'button', onclick: remove }, icon('trash'), "O'chirish"));
}

function renderProps() {
    const status = task.can_edit
        ? select('status', Object.entries(STATUS), task.status, { class: 'select sm', 'aria-label': 'Holati' })
        : el('span', { class: `pill status-${task.status}`, text: STATUS[task.status] });
    if (task.can_edit) status.addEventListener('change', () => update({ status: status.value }, 'Holat yangilandi'));

    const priority = task.can_edit
        ? select('priority', Object.entries(PRIORITY), task.priority, { class: 'select sm', 'aria-label': 'Muhimligi' })
        : priorityPill(task.priority);
    if (task.can_edit) priority.addEventListener('change', () => update({ priority: priority.value }, 'Muhimlik yangilandi'));

    const person = (name) => (name ? el('span', { class: 'row' }, avatar(name, { size: 'sm' }), name) : el('span', { class: 'muted', text: 'Tayinlanmagan' }));
    const prop = (label, value) => [el('dt', { text: label }), el('dd', {}, value)];

    clear($('#task-props'),
        prop('Holati', status),
        prop('Muhimligi', priority),
        prop('Muddat', task.due_date ? dueBadge(task.due_date, task.status) : el('span', { class: 'muted', text: "Belgilanmagan" })),
        prop('Loyiha', task.project ? el('a', { href: `/project/${task.project}/`, text: task.project_name }) : el('span', { class: 'muted', text: 'Shaxsiy' })),
        prop("Mas'ul", person(task.assigned_to_username)),
        prop('Yaratgan', task.created_by_username ? person(task.created_by_username) : el('span', { class: 'muted', text: "O'chirilgan foydalanuvchi" })),
        prop('Teglar', task.tags_detail.length ? el('div', { class: 'row wrap' }, task.tags_detail.map((t) => tagChip(t))) : el('span', { class: 'muted', text: "Yo'q" })),
        prop('Yaratilgan', el('span', { class: 'muted small', text: formatDateTime(task.created_at) })),
        prop('Yangilangan', el('span', { class: 'muted small', text: formatDateTime(task.updated_at) })));
}

function renderTask() {
    document.title = `${task.title} · Task Management`;
    $('#task-title').textContent = task.title;
    const description = $('#task-description');
    description.textContent = task.description || "Tavsif qo'shilmagan";
    description.classList.toggle('muted', !task.description);
    renderActions();
    renderProps();
    renderComments();
}

// ---------- Izohlar ----------
function commentNode(comment) {
    const mine = comment.user === currentUser.id;
    const canDelete = mine || ['owner', 'admin'].includes(myRole);
    const text = el('div', { class: 'text', text: comment.text });
    const node = el('div', { class: 'comment' },
        avatar(comment.username || '?'),
        el('div', { class: 'bubble' },
            el('div', { class: 'head' },
                el('strong', { text: comment.username || "O'chirilgan foydalanuvchi" }),
                el('span', { class: 'muted small', text: formatDateTime(comment.created_at) }),
                el('div', { class: 'tools' },
                    mine && el('button', { class: 'btn btn-ghost btn-icon btn-sm', type: 'button', title: 'Tahrirlash', onclick: () => editComment(comment, text) }, icon('edit', 14)),
                    canDelete && el('button', { class: 'btn btn-ghost btn-icon btn-sm', type: 'button', title: "O'chirish", onclick: () => deleteComment(comment) }, icon('trash', 14)))),
            text));
    return node;
}

function renderComments() {
    $('#comment-count').textContent = task.comments.length;
    clear($('#comments'), task.comments.length
        ? task.comments.map(commentNode)
        : emptyState("Hozircha izoh yo'q", 'Birinchi bo\'lib fikr bildiring', 'message'));
}

function editComment(comment, textNode) {
    const area = el('textarea', { class: 'textarea', maxlength: 2000 });
    area.value = comment.text;
    const save = el('button', { class: 'btn btn-primary btn-sm', type: 'button', text: 'Saqlash' });
    const cancel = el('button', { class: 'btn btn-sm', type: 'button', text: 'Bekor qilish', onclick: () => renderComments() });
    save.addEventListener('click', () => withLoading(save, async () => {
        try {
            const updated = await api.comments.update(comment.id, area.value.trim());
            Object.assign(comment, updated);
            renderComments();
        } catch (error) {
            showError(error);
        }
    }));
    textNode.replaceWith(el('div', { class: 'stack', style: { gap: '8px' } }, area, el('div', { class: 'row' }, save, cancel)));
    area.focus();
}

async function deleteComment(comment) {
    if (!(await confirmDialog("Izohni o'chirasizmi?"))) return;
    try {
        await api.comments.remove(comment.id);
        task.comments = task.comments.filter((c) => c.id !== comment.id);
        renderComments();
    } catch (error) {
        showError(error);
    }
}

const commentForm = $('#comment-form');
commentForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = commentForm.text.value.trim();
    if (!text) return;
    withLoading(commentForm.querySelector('button[type=submit]'), async () => {
        try {
            const comment = await api.comments.create(taskId, text);
            task.comments.push(comment);
            commentForm.reset();
            renderComments();
        } catch (error) {
            showError(error);
        }
    });
});
commentForm.text.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) commentForm.requestSubmit();
});

// ---------- Task amallari ----------
async function update(data, message) {
    try {
        const updated = await api.tasks.update(taskId, data);
        task = { ...task, ...updated };
        toast(message, 'success');
        renderTask();
    } catch (error) {
        showError(error);
        renderProps();
    }
}

async function edit() {
    const saved = await openTaskForm({ task, projects });
    if (saved) {
        task = { ...task, ...saved };
        renderTask();
    }
}

async function remove() {
    if (!(await confirmDialog(`"${task.title}" vazifasini o'chirasizmi?`))) return;
    try {
        await api.tasks.remove(taskId);
        toast("Vazifa o'chirildi", 'success');
        window.location.href = task.project ? `/project/${task.project}/` : '/tasks/';
    } catch (error) {
        showError(error);
    }
}

async function main() {
    const [{ projects: list }, loaded] = await Promise.all([initApp(), api.tasks.get(taskId)]);
    projects = list;
    task = loaded;
    myRole = projects.find((p) => p.id === task.project)?.my_role || null;
    if (task.project) $('main.content').dataset.projectId = task.project;
    renderTask();
}

main().catch(showError);
