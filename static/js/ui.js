// Umumiy UI yordamchilari: DOM yaratish, ikonlar, modal, toast, formatlash.
// Foydalanuvchi matni har doim textContent orqali qo'yiladi (XSS'dan himoya).

// ---------- Joriy foydalanuvchi ----------
export const currentUser = (() => {
    const node = document.getElementById('current-user');
    return node ? JSON.parse(node.textContent) : null;
})();

// ---------- DOM ----------
/**
 * el('button', {class: 'btn', onclick: fn, disabled: true}, 'Matn', childNode)
 * Maxsus kalitlar: class, text, dataset, style (obyekt), on* (hodisalar).
 */
export function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
        if (value === undefined || value === null || value === false) continue;
        if (key === 'class') node.className = value;
        else if (key === 'text') node.textContent = value;
        else if (key === 'dataset') Object.assign(node.dataset, value);
        else if (key === 'style') Object.assign(node.style, value);
        else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
        else if (key in node && typeof value !== 'string') node[key] = value;
        else node.setAttribute(key, value === true ? '' : value);
    }
    append(node, children);
    return node;
}

function append(node, children) {
    for (const child of children.flat()) {
        if (child === null || child === undefined || child === false) continue;
        node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
}

export const $ = (selector, root = document) => root.querySelector(selector);

export function clear(node, ...children) {
    node.replaceChildren();
    append(node, children);
    return node;
}

// ---------- Ikonlar (statik SVG, foydalanuvchi ma'lumoti emas) ----------
const ICONS = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    check: '<path d="m5 12 5 5L20 7"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4Z"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z"/>',
    list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    board: '<rect x="3" y="3" width="7" height="18" rx="1"/><rect x="14" y="3" width="7" height="11" rx="1"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/>',
    tag: '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    crown: '<path d="m2 18 2-11 5 5 3-7 3 7 5-5 2 11Z"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1Z"/>',
    arrowLeft: '<path d="M19 12H5M12 19l-7-7 7-7"/>',
};

export function icon(name, size = 16) {
    const wrapper = document.createElement('span');
    wrapper.innerHTML = `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ''}</svg>`;
    return wrapper.firstElementChild;
}

// ---------- Yorliqlar ----------
export const STATUS = { todo: 'Bajarilishi kerak', in_progress: 'Jarayonda', done: 'Bajarildi' };
export const PRIORITY = { high: 'Yuqori', medium: "O'rta", low: 'Past' };
export const ROLE = { owner: 'Egasi', admin: 'Admin', member: "A'zo" };

export const statusPill = (status) => el('span', { class: `pill status-${status}`, text: STATUS[status] });
export const priorityPill = (priority) =>
    el('span', { class: `pill priority-${priority}`, text: PRIORITY[priority] });
export const rolePill = (role) => el('span', { class: `pill plain role-${role}`, text: ROLE[role] || role });

// ---------- Avatar ----------
const AVATAR_COLORS = ['#4f46e5', '#0891b2', '#059669', '#d97706', '#dc2626', '#7c3aed', '#db2777', '#2563eb'];

export function avatar(name, { size = '', src = null } = {}) {
    const label = name || '?';
    let hash = 0;
    for (const char of label) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
    const node = el('span', {
        class: `avatar ${size}`,
        title: label,
        style: { background: AVATAR_COLORS[hash % AVATAR_COLORS.length] },
    });
    if (src) node.append(el('img', { src, alt: '' }));
    else node.textContent = label.charAt(0).toUpperCase();
    return node;
}

export function tagChip(tag, onRemove) {
    return el(
        'span',
        { class: 'chip' },
        el('span', { class: 'swatch', style: { background: tag.color } }),
        tag.name,
        onRemove && el('button', { type: 'button', title: 'Olib tashlash', onclick: onRemove }, icon('x', 12)),
    );
}

// ---------- Sana ----------
const pad = (n) => String(n).padStart(2, '0');

export function todayISO() {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function formatDate(value) {
    if (!value) return '';
    const d = new Date(value.length === 10 ? `${value}T00:00:00` : value);
    return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

export function formatDateTime(value) {
    const d = new Date(value);
    return `${formatDate(value)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Muddat belgisi: "Bugun", "Ertaga", "2 kun kechikdi" va h.k. */
export function dueBadge(dueDate, status) {
    if (!dueDate) return null;
    const days = Math.round((new Date(`${dueDate}T00:00:00`) - new Date(`${todayISO()}T00:00:00`)) / 86400000);
    const open = status !== 'done';
    let text = formatDate(dueDate);
    let cls = 'due';
    if (open && days < 0) {
        text = `${-days} kun kechikdi`;
        cls += ' overdue';
    } else if (open && days === 0) {
        text = 'Bugun';
        cls += ' today';
    } else if (open && days === 1) {
        text = 'Ertaga';
    }
    return el('span', { class: cls, title: formatDate(dueDate) }, icon('calendar', 12), text);
}

// ---------- Toast ----------
export function toast(message, type = '') {
    let container = $('.toasts');
    if (!container) {
        container = el('div', { class: 'toasts', role: 'status', 'aria-live': 'polite' });
        document.body.append(container);
    }
    const node = el('div', { class: `toast ${type}` }, message);
    container.append(node);
    setTimeout(() => node.remove(), type === 'error' ? 6000 : 3000);
}

export const showError = (error) => toast(error.message || String(error), 'error');

// ---------- Modal ----------
/**
 * openModal({title, body, submitText, danger, onSubmit}) — onSubmit(form) Promise qaytarsa,
 * u tugaguncha tugma "yuklanmoqda" holatida turadi; xato bo'lsa modal ichida ko'rsatiladi.
 */
export function openModal({ title, body, submitText = 'Saqlash', danger = false, onSubmit, onClose, cancelText = 'Bekor qilish' }) {
    const errorBox = el('div', { class: 'form-error hidden' });
    const submit = el('button', { class: `btn ${danger ? 'btn-danger' : 'btn-primary'}`, type: 'submit', text: submitText });
    const form = el(
        'form',
        { method: 'dialog', novalidate: false },
        el('div', { class: 'modal-header' },
            el('h2', { text: title }),
            el('button', { class: 'btn btn-ghost btn-icon', type: 'button', 'aria-label': 'Yopish', onclick: () => close() }, icon('x'))),
        el('div', { class: 'modal-body stack' }, errorBox, body),
        el('div', { class: 'modal-footer' },
            el('button', { class: 'btn', type: 'button', text: cancelText, onclick: () => close() }),
            onSubmit && submit),
    );
    const dialog = el('dialog', { class: 'modal' }, form);
    document.body.append(dialog);

    function close() {
        dialog.close();
        dialog.remove();
        if (onClose) onClose();
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!onSubmit) return close();
        errorBox.classList.add('hidden');
        submit.classList.add('loading');
        try {
            const keepOpen = await onSubmit(form);
            if (keepOpen !== true) close();
        } catch (error) {
            errorBox.textContent = error.message;
            errorBox.classList.remove('hidden');
        } finally {
            submit.classList.remove('loading');
        }
    });
    dialog.addEventListener('cancel', (event) => {
        event.preventDefault();
        close();
    });
    dialog.showModal();
    const firstInput = form.querySelector('input:not([type=hidden]), textarea, select');
    if (firstInput) firstInput.focus();
    return { close, form };
}

export function confirmDialog(message, { title = 'Tasdiqlang', confirmText = "O'chirish", danger = true } = {}) {
    return new Promise((resolve) => {
        let answered = false;
        openModal({
            title,
            body: el('p', { text: message }),
            submitText: confirmText,
            danger,
            onSubmit: async () => {
                answered = true;
                resolve(true);
            },
            onClose: () => answered || resolve(false),
        });
    });
}

// ---------- Formalar ----------
export function field(label, input, hint) {
    return el('div', { class: 'field' }, el('label', { text: label, for: input.id || undefined }), input, hint && el('div', { class: 'hint', text: hint }));
}

export function select(name, options, value, props = {}) {
    return el(
        'select',
        { class: 'select', name, ...props },
        options.map(([optionValue, label]) =>
            el('option', { value: optionValue, text: label, selected: String(optionValue) === String(value ?? '') }),
        ),
    );
}

export function formData(form) {
    return Object.fromEntries(new FormData(form).entries());
}

// ---------- Boshqalar ----------
export function debounce(fn, ms = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}

export function emptyState(title, text, iconName = 'inbox') {
    return el('div', { class: 'empty' }, icon(iconName, 40), el('div', { class: 'title', text: title }), text && el('div', { text }));
}

export function skeletonRows(count = 4) {
    return el('div', { class: 'card-body stack' }, Array.from({ length: count }, (_, i) =>
        el('div', { class: 'skeleton', style: { width: `${90 - i * 12}%` } })));
}

/** Tugmani so'rov davomida bloklab turadi. */
export async function withLoading(button, fn) {
    button.classList.add('loading');
    button.disabled = true;
    try {
        return await fn();
    } finally {
        button.classList.remove('loading');
        button.disabled = false;
    }
}
