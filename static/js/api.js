// REST API bilan ishlash uchun yagona joy. Barcha sahifalar shu modul orqali so'rov yuboradi.

export class ApiError extends Error {
    constructor(status, data) {
        super(formatErrors(data) || `Xatolik yuz berdi (${status})`);
        this.status = status;
        this.data = data;
    }

    /** Maydon bo'yicha xato matni: {title: ["..."]} → "..." */
    field(name) {
        const value = this.data && this.data[name];
        return Array.isArray(value) ? value.join(' ') : value || '';
    }
}

const FIELD_LABELS = {
    title: 'Nomi', name: 'Nomi', username: 'Username', email: 'Email', password: 'Parol',
    password2: 'Parol (takror)', assigned_to: "Mas'ul", project: 'Loyiha', tags: 'Teglar',
    due_date: 'Muddat', text: 'Izoh', user: 'Foydalanuvchi', role: 'Rol', avatar: 'Rasm',
    color: 'Rang', description: 'Tavsif',
};

function formatErrors(data) {
    if (!data) return '';
    if (typeof data === 'string') return data;
    if (Array.isArray(data)) return data.join(' ');
    if (data.detail) return data.detail;
    return Object.entries(data)
        .map(([key, value]) => {
            const text = Array.isArray(value) ? value.join(' ') : String(value);
            return key === 'non_field_errors' ? text : `${FIELD_LABELS[key] || key}: ${text}`;
        })
        .join('\n');
}

function csrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
}

export async function request(path, { method = 'GET', body, params } = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '' && value !== false) {
            url.searchParams.set(key, value);
        }
    });

    const headers = { Accept: 'application/json' };
    const isForm = body instanceof FormData;
    if (body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
    if (method !== 'GET') headers['X-CSRFToken'] = csrfToken();

    const response = await fetch(url, {
        method,
        headers,
        credentials: 'same-origin',
        body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });

    if (response.status === 204) return null;
    let data = null;
    try {
        data = await response.json();
    } catch {
        /* javob JSON emas */
    }
    if (!response.ok) throw new ApiError(response.status, data);
    return data;
}

const get = (path, params) => request(path, { params });
const post = (path, body) => request(path, { method: 'POST', body });
const patch = (path, body) => request(path, { method: 'PATCH', body });
const del = (path) => request(path, { method: 'DELETE' });

export const auth = {
    login: (username, password) => post('/api/accounts/login/', { username, password }),
    logout: () => post('/api/accounts/logout/'),
    register: (data) => post('/api/accounts/register/', data),
    profile: () => get('/api/accounts/profile/'),
    updateProfile: (data) => patch('/api/accounts/profile/', data),
};

export const projects = {
    list: (params) => get('/api/projects/', params),
    get: (id) => get(`/api/projects/${id}/`),
    create: (data) => post('/api/projects/', data),
    update: (id, data) => patch(`/api/projects/${id}/`, data),
    remove: (id) => del(`/api/projects/${id}/`),
    members: (id) => get(`/api/projects/${id}/members/`),
    changeRole: (id, memberId, role) => patch(`/api/projects/${id}/members/${memberId}/`, { role }),
    removeMember: (id, memberId) => del(`/api/projects/${id}/members/${memberId}/`),
    transferOwnership: (id, memberId) =>
        post(`/api/projects/${id}/transfer-ownership/`, { member_id: memberId }),
    invitations: (id) => get(`/api/projects/${id}/invitations/`),
    invite: (id, user, role) => post(`/api/projects/${id}/invitations/`, { user, role }),
    cancelInvitation: (id, invitationId) => del(`/api/projects/${id}/invitations/${invitationId}/`),
};

export const invitations = {
    mine: () => get('/api/invitations/'),
    accept: (id) => post(`/api/invitations/${id}/accept/`),
    decline: (id) => post(`/api/invitations/${id}/decline/`),
};

export const tasks = {
    /** Sahifalangan: {count, next, previous, results} */
    list: (params) => get('/api/tasks/', params),
    next: (url) => request(url),
    get: (id) => get(`/api/tasks/${id}/`),
    create: (data) => post('/api/tasks/', data),
    update: (id, data) => patch(`/api/tasks/${id}/`, data),
    remove: (id) => del(`/api/tasks/${id}/`),
    stats: (params) => get('/api/tasks/stats/', params),
};

export const tags = {
    list: () => get('/api/tags/'),
    create: (data) => post('/api/tags/', data),
    update: (id, data) => patch(`/api/tags/${id}/`, data),
    remove: (id) => del(`/api/tags/${id}/`),
};

export const comments = {
    create: (task, text) => post('/api/comments/', { task, text }),
    update: (id, text) => patch(`/api/comments/${id}/`, { text }),
    remove: (id) => del(`/api/comments/${id}/`),
};
