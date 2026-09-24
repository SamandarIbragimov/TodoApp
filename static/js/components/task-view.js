// Tasklar ko'rinishi: filtrlar + ro'yxat/doska + statistika.
// "Mening vazifalarim" va loyiha sahifasi shu komponentdan foydalanadi.
import * as api from '../api.js';
import {
    avatar, clear, confirmDialog, debounce, dueBadge, el, emptyState, icon, PRIORITY,
    priorityPill, select, showError, skeletonRows, STATUS, statusPill, tagChip, toast,
} from '../ui.js';
import { openTaskForm } from './task-form.js';

const FILTER_KEYS = ['search', 'status', 'priority', 'due_date_from', 'due_date_to', 'mine', 'ordering', 'personal'];
const BOARD_LIMIT = 100;

// ---------- Statistika ----------
export async function renderStats(container, params = {}) {
    try {
        const s = await api.tasks.stats(params);
        const done = s.by_status.done || 0;
        const percent = s.total ? Math.round((done / s.total) * 100) : 0;
        const stat = (value, label, cls = '') => el('div', { class: `stat ${cls}` }, el('div', { class: 'value', text: value }), el('div', { class: 'label', text: label }));
        clear(container,
            stat(s.total, 'Jami vazifa', 'accent'),
            stat(s.by_status.in_progress || 0, 'Jarayonda', 'warning'),
            el('div', { class: 'stat success' },
                el('div', { class: 'value', text: `${percent}%` }),
                el('div', { class: 'label', text: `Bajarildi: ${done} ta` }),
                el('div', { class: 'progress', style: { marginTop: '8px' } }, el('span', { style: { width: `${percent}%` } }))),
            stat(s.due_today, 'Bugun muddati', s.due_today ? 'warning' : ''),
            stat(s.overdue, "Muddati o'tgan", s.overdue ? 'danger' : ''));
    } catch (error) {
        showError(error);
    }
}

// ---------- Asosiy komponent ----------
/**
 * @param {object} options
 * @param {HTMLElement} options.root
 * @param {Array} options.projects       foydalanuvchi loyihalari (task formasi uchun)
 * @param {number} [options.projectId]   faqat shu loyiha tasklari
 * @param {HTMLElement} [options.statsContainer]
 * @param {'list'|'board'} [options.defaultView]
 */
export function createTaskView({ root, projects, projectId = null, statsContainer = null, defaultView = 'list' }) {
    const url = new URL(window.location.href);
    const filters = Object.fromEntries(FILTER_KEYS.map((key) => [key, url.searchParams.get(key) || '']));
    let view = url.searchParams.get('view') || defaultView;
    let nextPage = null;

    const baseParams = () => ({ ...filters, project: projectId || '' });

    // --- Toolbar ---
    const searchInput = el('input', { class: 'input sm', type: 'search', placeholder: 'Qidirish...', value: filters.search });
    const statusSelect = select('status', [['', 'Barcha holatlar'], ...Object.entries(STATUS)], filters.status, { class: 'select sm' });
    const prioritySelect = select('priority', [['', 'Barcha muhimlik'], ...Object.entries(PRIORITY)], filters.priority, { class: 'select sm' });
    const fromInput = el('input', { class: 'input sm', type: 'date', title: 'Muddat (dan)', value: filters.due_date_from });
    const toInput = el('input', { class: 'input sm', type: 'date', title: 'Muddat (gacha)', value: filters.due_date_to });
    const orderingSelect = select('ordering', [
        ['', 'Yangilari birinchi'], ['due_date', "Muddat bo'yicha"], ['-priority', 'Muhimlari birinchi'], ['status', "Holat bo'yicha"],
    ], filters.ordering, { class: 'select sm' });
    const mineBox = el('input', { type: 'checkbox', checked: filters.mine === 'true' });
    const scopeSelect = projectId ? null : select('personal', [['', 'Barcha vazifalar'], ['true', 'Faqat shaxsiy'], ['false', 'Faqat loyihalar']], filters.personal, { class: 'select sm' });
    const viewToggle = el('div', { class: 'segmented', role: 'group', 'aria-label': "Ko'rinish" },
        el('button', { type: 'button', dataset: { view: 'list' } }, icon('list', 14), "Ro'yxat"),
        el('button', { type: 'button', dataset: { view: 'board' } }, icon('board', 14), 'Doska'));

    const toolbar = el('div', {},
        el('div', { class: 'toolbar' },
            el('div', { class: 'search' }, icon('search', 14), searchInput),
            el('label', { class: 'checkbox small' }, mineBox, 'Menga tayinlangan'),
            viewToggle),
        el('div', { class: 'toolbar' },
            statusSelect, prioritySelect, scopeSelect,
            el('span', { class: 'muted small', text: 'Muddat:' }), fromInput, el('span', { class: 'muted', text: '—' }), toInput,
            el('div', { class: 'spacer' }),
            orderingSelect));
    const body = el('div');
    const loadMore = el('div', { class: 'load-more hidden' },
        el('button', { class: 'btn btn-sm', type: 'button', text: "Ko'proq yuklash", onclick: () => loadNext() }));
    clear(root, el('div', { class: 'card' }, toolbar, body, loadMore));

    // --- Filtr o'zgarishlari ---
    function syncUrl() {
        const next = new URL(window.location.href);
        FILTER_KEYS.forEach((key) => (filters[key] ? next.searchParams.set(key, filters[key]) : next.searchParams.delete(key)));
        next.searchParams.set('view', view);
        history.replaceState(null, '', next);
    }

    function setFilter(key, value) {
        filters[key] = value;
        syncUrl();
        reload();
    }

    searchInput.addEventListener('input', debounce(() => setFilter('search', searchInput.value.trim()), 350));
    statusSelect.addEventListener('change', () => setFilter('status', statusSelect.value));
    prioritySelect.addEventListener('change', () => setFilter('priority', prioritySelect.value));
    fromInput.addEventListener('change', () => setFilter('due_date_from', fromInput.value));
    toInput.addEventListener('change', () => setFilter('due_date_to', toInput.value));
    orderingSelect.addEventListener('change', () => setFilter('ordering', orderingSelect.value));
    mineBox.addEventListener('change', () => setFilter('mine', mineBox.checked ? 'true' : ''));
    if (scopeSelect) scopeSelect.addEventListener('change', () => setFilter('personal', scopeSelect.value));
    viewToggle.addEventListener('click', (event) => {
        const button = event.target.closest('button');
        if (!button || button.dataset.view === view) return;
        view = button.dataset.view;
        syncUrl();
        reload();
    });

    // --- Amallar ---
    async function changed() {
        await reload();
        if (statsContainer) renderStats(statsContainer, { project: projectId || '' });
    }

    async function editTask(task) {
        const saved = await openTaskForm({ task, projects });
        if (saved) changed();
    }

    async function deleteTask(task) {
        if (!(await confirmDialog(`"${task.title}" vazifasini o'chirasizmi? Bu amalni qaytarib bo'lmaydi.`))) return;
        try {
            await api.tasks.remove(task.id);
            toast("Vazifa o'chirildi", 'success');
            changed();
        } catch (error) {
            showError(error);
        }
    }

    async function setStatus(task, status) {
        try {
            await api.tasks.update(task.id, { status });
            changed();
        } catch (error) {
            showError(error);
        }
    }

    // --- Ro'yxat ko'rinishi ---
    function taskMeta(task, { showStatus = true } = {}) {
        return el('div', { class: 'meta' },
            showStatus && statusPill(task.status),
            priorityPill(task.priority),
            dueBadge(task.due_date, task.status),
            !projectId && task.project && el('a', { class: 'pill plain', href: `/project/${task.project}/`, text: task.project_name }),
            task.tags_detail.map((tag) => tagChip(tag)),
            task.comments_count ? el('span', { class: 'due' }, icon('message', 12), task.comments_count) : null);
    }

    function taskRow(task) {
        const done = task.status === 'done';
        return el('li', { class: `task-row ${done ? 'done' : ''}` },
            el('button', {
                class: `check ${done ? 'checked' : ''}`,
                type: 'button',
                title: done ? 'Bajarilmagan deb belgilash' : 'Bajarildi deb belgilash',
                disabled: !task.can_edit,
                onclick: () => setStatus(task, done ? 'todo' : 'done'),
            }, icon('check', 12)),
            el('div', { style: { minWidth: 0 } },
                el('a', { class: 'title', href: `/tasks/${task.id}/`, text: task.title }),
                taskMeta(task)),
            el('div', { class: 'side' },
                el('div', { class: 'row-actions' },
                    task.can_edit && el('button', { class: 'btn btn-ghost btn-icon btn-sm', type: 'button', title: 'Tahrirlash', onclick: () => editTask(task) }, icon('edit', 14)),
                    task.can_delete && el('button', { class: 'btn btn-ghost btn-icon btn-sm', type: 'button', title: "O'chirish", onclick: () => deleteTask(task) }, icon('trash', 14))),
                task.assigned_to_username
                    ? avatar(task.assigned_to_username, { size: 'sm' })
                    : el('span', { class: 'avatar sm', title: 'Tayinlanmagan', style: { border: '1px dashed var(--border-strong)' } })));
    }

    async function renderList(current) {
        const page = await api.tasks.list(baseParams());
        if (current !== requestId) return; // bu orada yangi filtr tanlangan
        nextPage = page.next;
        const list = el('ul', { class: 'task-list' }, page.results.map(taskRow));
        clear(body, page.results.length ? list : emptyState('Vazifalar topilmadi', hasFilters() ? "Filtrlarni o'zgartirib ko'ring" : "Birinchi vazifani qo'shing"));
        loadMore.classList.toggle('hidden', !nextPage);
    }

    async function loadNext() {
        if (!nextPage) return;
        try {
            const page = await api.tasks.next(nextPage);
            nextPage = page.next;
            body.querySelector('.task-list').append(...page.results.map(taskRow));
            loadMore.classList.toggle('hidden', !nextPage);
        } catch (error) {
            showError(error);
        }
    }

    // --- Doska (Kanban) ko'rinishi ---
    function taskCard(task) {
        const card = el('div', {
            class: 'task-card',
            draggable: task.can_edit ? 'true' : 'false',
            dataset: { id: task.id },
            onclick: (event) => {
                if (!event.target.closest('a, button')) window.location.href = `/tasks/${task.id}/`;
            },
        },
        el('a', { class: 'title', href: `/tasks/${task.id}/`, text: task.title }),
        taskMeta(task, { showStatus: false }),
        el('div', { class: 'foot' },
            // Loyiha sahifasida loyiha nomi ortiqcha
            el('span', { class: 'muted small', text: projectId ? '' : task.project_name || 'Shaxsiy' }),
            task.assigned_to_username ? avatar(task.assigned_to_username, { size: 'sm' }) : null));
        card.addEventListener('dragstart', (event) => {
            event.dataTransfer.setData('text/plain', String(task.id));
            card.classList.add('dragging');
        });
        card.addEventListener('dragend', () => card.classList.remove('dragging'));
        return card;
    }

    async function renderBoard(current) {
        const page = await api.tasks.list({ ...baseParams(), status: '', page_size: BOARD_LIMIT });
        if (current !== requestId) return;
        nextPage = null;
        loadMore.classList.add('hidden');
        const byId = new Map(page.results.map((t) => [String(t.id), t]));

        const columns = Object.entries(STATUS).map(([status, label]) => {
            const items = page.results.filter((t) => t.status === status);
            const column = el('div', { class: 'column', dataset: { status } },
                el('div', { class: 'column-header' },
                    el('div', { class: 'row' }, statusPill(status)),
                    el('span', { class: 'badge soft', text: items.length })),
                items.map(taskCard),
                !items.length && el('div', { class: 'muted small', style: { textAlign: 'center', padding: '16px 0' }, text: label === STATUS.done ? "Hali bajarilgan vazifa yo'q" : "Bo'sh" }));
            column.addEventListener('dragover', (event) => {
                event.preventDefault();
                column.classList.add('drop-target');
            });
            column.addEventListener('dragleave', () => column.classList.remove('drop-target'));
            column.addEventListener('drop', (event) => {
                event.preventDefault();
                column.classList.remove('drop-target');
                const task = byId.get(event.dataTransfer.getData('text/plain'));
                if (task && task.status !== status) setStatus(task, status);
            });
            return column;
        });
        const note = page.count > BOARD_LIMIT
            ? el('div', { class: 'muted small', style: { padding: '0 16px 12px' }, text: `Doskada birinchi ${BOARD_LIMIT} ta vazifa ko'rsatilgan. Qolganlari uchun filtrlardan foydalaning.` })
            : null;
        clear(body, el('div', { class: 'board' }, columns), note);
    }

    // --- Yuklash ---
    function hasFilters() {
        return FILTER_KEYS.some((key) => key !== 'ordering' && filters[key]);
    }

    let requestId = 0;
    async function reload() {
        const current = ++requestId;
        viewToggle.querySelectorAll('button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
        statusSelect.classList.toggle('hidden', view === 'board');
        if (!body.childElementCount) body.append(skeletonRows());
        try {
            await (view === 'board' ? renderBoard(current) : renderList(current));
        } catch (error) {
            if (current === requestId) {
                clear(body, emptyState('Yuklab bo\'lmadi', error.message));
                showError(error);
            }
        }
    }

    reload();
    if (statsContainer) renderStats(statsContainer, { project: projectId || '' });

    return {
        reload: changed,
        async create(defaults = {}) {
            const saved = await openTaskForm({ projectId, projects, defaults });
            if (saved) changed();
        },
    };
}
