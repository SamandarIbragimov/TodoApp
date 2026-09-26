import * as api from '../api.js';
import { createProject, initApp, refreshSidebar } from '../app.js';
import { openTaskForm } from '../components/task-form.js';
import { renderStats } from '../components/task-view.js';
import {
    $, clear, dueBadge, el, emptyState, icon, priorityPill, rolePill, ROLE, showError, skeletonRows,
    toast, withLoading,
} from '../ui.js';

const MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];
const WEEKDAYS = ['yakshanba', 'dushanba', 'seshanba', 'chorshanba', 'payshanba', 'juma', 'shanba'];

let projects = [];

function renderToday() {
    const d = new Date();
    $('#today').textContent = `Bugun ${d.getDate()}-${MONTHS[d.getMonth()]}, ${WEEKDAYS[d.getDay()]}`;
}

// Takliflar bo'limi vaqtincha yashirilgan; qayta yoqish uchun true qiling
const INVITATIONS_ENABLED = false;

function renderInvitations(invitations) {
    if (!INVITATIONS_ENABLED) return;
    const section = $('#invitations');
    section.classList.toggle('hidden', invitations.length === 0);
    clear(section, invitations.map((invitation) => {
        const accept = el('button', { class: 'btn btn-primary btn-sm', type: 'button', text: 'Qabul qilish' });
        const decline = el('button', { class: 'btn btn-sm', type: 'button', text: 'Rad etish' });
        accept.addEventListener('click', () => respond(accept, invitation, 'accept'));
        decline.addEventListener('click', () => respond(decline, invitation, 'decline'));
        return el('div', { class: 'invite-card' },
            el('span', { class: 'brand-mark' }, icon('mail', 16)),
            el('div', { class: 'grow' },
                el('div', {},
                    el('strong', { text: invitation.invited_by || 'Kimdir' }),
                    ' sizni ',
                    el('strong', { text: invitation.project_name }),
                    ` loyihasiga ${ROLE[invitation.role].toLowerCase()} sifatida taklif qildi`)),
            el('div', { class: 'row' }, decline, accept));
    }));
}

async function respond(button, invitation, action) {
    await withLoading(button, async () => {
        try {
            await api.invitations[action](invitation.id);
            toast(action === 'accept' ? `"${invitation.project_name}" loyihasiga qo'shildingiz` : 'Taklif rad etildi', 'success');
            await load();
        } catch (error) {
            showError(error);
        }
    });
}

function renderProjects() {
    $('#project-count').textContent = projects.length;
    const newCard = el('button', { class: 'card project-card new', type: 'button', onclick: createProject },
        icon('plus', 24), el('span', { text: 'Yangi loyiha yaratish' }));
    clear($('#projects'),
        projects.map((project) => el('a', { class: 'card project-card', href: `/project/${project.id}/` },
            el('div', { class: 'row' },
                el('span', { class: 'brand-mark' }, icon('folder', 16)),
                el('h3', { text: project.name, style: { flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }),
                rolePill(project.my_role)),
            el('div', { class: 'desc', text: project.description || "Tavsif yo'q" }),
            el('div', { class: 'row muted small' }, icon('users', 14), `${project.members_count} a'zo`))),
        newCard);
}

async function renderUpcoming() {
    const container = $('#upcoming');
    clear(container, skeletonRows(3));
    try {
        // Muddati bor, bajarilmagan tasklar — eng yaqini birinchi (muddati o'tganlar ham).
        // due_date_to muddatsiz tasklarni chiqarib tashlash uchun berilgan
        const page = await api.tasks.list({ ordering: 'due_date', due_date_to: '2999-12-31', page_size: 30 });
        const open = page.results.filter((t) => t.status !== 'done').slice(0, 7);
        clear(container, open.length
            ? el('ul', { class: 'task-list' }, open.map((task) =>
                el('li', { class: 'task-row', style: { gridTemplateColumns: 'minmax(0, 1fr) auto' } },
                    el('div', { style: { minWidth: 0 } },
                        el('a', { class: 'title', href: `/tasks/${task.id}/`, text: task.title }),
                        el('div', { class: 'meta' }, dueBadge(task.due_date, task.status), el('span', { class: 'muted small', text: task.project_name || 'Shaxsiy' }))),
                    priorityPill(task.priority))))
            : emptyState('Hammasi joyida', "Yaqin muddatli vazifalar yo'q", 'calendar'));
    } catch (error) {
        showError(error);
    }
}

async function load() {
    const { projects: list, invitations } = await refreshSidebar();
    projects = list;
    renderInvitations(invitations);
    renderProjects();
    renderStats($('#stats'));
    renderUpcoming();
}

$('#new-project').addEventListener('click', createProject);
$('#new-task').addEventListener('click', async () => {
    const saved = await openTaskForm({ projects });
    if (saved) {
        renderStats($('#stats'));
        renderUpcoming();
    }
});

renderToday();
initApp().then(({ projects: list, invitations }) => {
    projects = list;
    renderInvitations(invitations);
    renderProjects();
    renderStats($('#stats'));
    renderUpcoming();
    if (INVITATIONS_ENABLED && window.location.hash === '#invitations' && invitations.length) $('#invitations').scrollIntoView();
});
