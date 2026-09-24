// Ilova karkasi: yon panel, mavzu, chiqish. Har bir sahifa skripti buni import qiladi.
import * as api from './api.js';
import { openProjectForm } from './components/project-form.js';
import { $, avatar, clear, currentUser, el, icon, showError } from './ui.js';

const app = $('#app');

function setupIcons() {
    document.querySelectorAll('[data-icon]').forEach((node) => node.prepend(icon(node.dataset.icon, 18)));
    $('#sidebar-new-project').append(icon('plus', 14));
    $('#menu-toggle').append(icon('menu', 20));
}

function setupActiveNav() {
    const page = $('main.content')?.dataset.page;
    document.querySelectorAll('[data-nav]').forEach((link) => {
        link.classList.toggle('active', link.dataset.nav === page);
    });
}

function setupTheme() {
    const button = $('#theme-toggle');
    const render = () => {
        const dark = document.documentElement.dataset.theme === 'dark';
        clear(button, icon(dark ? 'sun' : 'moon', 18), dark ? "Yorug' mavzu" : "Qorong'i mavzu");
    };
    button.addEventListener('click', () => {
        const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = next;
        try {
            localStorage.setItem('theme', next);
        } catch {
            /* brauzer xotirasi yopiq — mavzu faqat shu sahifada o'zgaradi */
        }
        render();
    });
    render();
}

function setupMobileMenu() {
    $('#menu-toggle').addEventListener('click', () => app.classList.toggle('nav-open'));
    app.addEventListener('click', (event) => {
        if (app.classList.contains('nav-open') && !event.target.closest('.sidebar, #menu-toggle')) {
            app.classList.remove('nav-open');
        }
    });
}

function setupLogout() {
    $('#logout').addEventListener('click', async () => {
        try {
            await api.auth.logout();
        } finally {
            window.location.href = '/accounts/login/';
        }
    });
}

export async function refreshSidebar() {
    const container = $('#sidebar-projects');
    try {
        const [projects, invitations] = await Promise.all([api.projects.list(), api.invitations.mine()]);
        const currentId = $('main.content')?.dataset.projectId;
        clear(
            container,
            projects.length
                ? projects.map((project) =>
                    el('a', {
                        class: `nav-link ${String(project.id) === currentId ? 'active' : ''}`,
                        href: `/project/${project.id}/`,
                    }, el('span', { class: 'dot', style: { background: 'var(--primary)' } }), el('span', { class: 'name', text: project.name })))
                : el('div', { class: 'muted small', style: { padding: '4px 10px' }, text: "Hozircha loyiha yo'q" }),
        );
        const badge = $('#invitation-count');
        badge.textContent = invitations.length;
        badge.classList.toggle('hidden', invitations.length === 0);
        return { projects, invitations };
    } catch (error) {
        clear(container, el('div', { class: 'muted small', style: { padding: '4px 10px' }, text: 'Yuklab bo\'lmadi' }));
        showError(error);
        return { projects: [], invitations: [] };
    }
}

async function createProject() {
    const project = await openProjectForm();
    if (project) window.location.href = `/project/${project.id}/`;
}

export function initApp() {
    setupIcons();
    setupActiveNav();
    setupTheme();
    setupMobileMenu();
    setupLogout();
    $('#sidebar-avatar').append(avatar(currentUser.username, { src: currentUser.avatar }));
    $('#sidebar-new-project').addEventListener('click', createProject);
    return refreshSidebar();
}

export { createProject };
