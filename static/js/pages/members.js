import * as api from '../api.js';
import { initApp, refreshSidebar } from '../app.js';
import {
    $, avatar, clear, confirmDialog, currentUser, el, emptyState, formData, formatDate, icon, ROLE,
    rolePill, select, showError, toast, withLoading,
} from '../ui.js';

const projectId = JSON.parse($('#project-id').textContent);
$('main.content').dataset.projectId = projectId;

let myRole = null;

async function run(action, successMessage) {
    try {
        await action();
        if (successMessage) toast(successMessage, 'success');
        await load();
        refreshSidebar();
    } catch (error) {
        showError(error);
    }
}

function memberActions(member) {
    const isMe = member.user_id === currentUser.id;
    const actions = [];
    if (member.role === 'owner') return actions;

    if (myRole === 'owner') {
        const roleSelect = select('role', [['admin', ROLE.admin], ['member', ROLE.member]], member.role, { class: 'select sm', style: { width: 'auto' }, 'aria-label': 'Rol' });
        roleSelect.addEventListener('change', () =>
            run(() => api.projects.changeRole(projectId, member.id, roleSelect.value), 'Rol o\'zgartirildi'));
        actions.push(roleSelect);
        actions.push(el('button', {
            class: 'btn btn-ghost btn-icon btn-sm', type: 'button', title: "Egalikni o'tkazish",
            onclick: async () => {
                const ok = await confirmDialog(
                    `Loyiha egaligi ${member.username} ga o'tadi, siz esa admin bo'lib qolasiz. Davom etasizmi?`,
                    { title: "Egalikni o'tkazish", confirmText: "O'tkazish" },
                );
                if (ok) run(() => api.projects.transferOwnership(projectId, member.id), "Egalik o'tkazildi");
            },
        }, icon('crown', 14)));
    }

    const canRemove = isMe || myRole === 'owner' || (myRole === 'admin' && member.role === 'member');
    if (canRemove) {
        actions.push(el('button', {
            class: 'btn btn-ghost btn-icon btn-sm', type: 'button', title: isMe ? 'Loyihadan chiqish' : 'Chiqarish',
            onclick: async () => {
                const message = isMe
                    ? "Loyihadan chiqasizmi? Qayta qo'shilish uchun yangi taklif kerak bo'ladi."
                    : `${member.username} loyihadan chiqariladi. Unga tayinlangan vazifalar tayinlovsiz qoladi.`;
                if (!(await confirmDialog(message, { confirmText: isMe ? 'Chiqish' : 'Chiqarish' }))) return;
                try {
                    await api.projects.removeMember(projectId, member.id);
                    if (isMe) {
                        window.location.href = '/';
                        return;
                    }
                    toast(`${member.username} chiqarildi`, 'success');
                    load();
                } catch (error) {
                    showError(error);
                }
            },
        }, icon(isMe ? 'logout' : 'trash', 14)));
    }
    return actions;
}

function renderMembers(members) {
    $('#member-count').textContent = members.length;
    clear($('#members'), members.map((member) => el('li', { class: 'list-item' },
        avatar(member.username),
        el('div', { class: 'grow' },
            el('div', { style: { fontWeight: 600 } }, member.username, member.user_id === currentUser.id ? el('span', { class: 'muted', text: ' (siz)' }) : null),
            el('div', { class: 'muted small', text: `${member.email || ''} · ${formatDate(member.joined_at)} dan beri` })),
        myRole === 'owner' && member.role !== 'owner' ? null : rolePill(member.role),
        el('div', { class: 'row' }, memberActions(member)))));
}

function renderPending(invitations) {
    clear($('#pending'), invitations.length
        ? invitations.map((invitation) => el('li', { class: 'list-item' },
            avatar(invitation.username, { size: 'sm' }),
            el('div', { class: 'grow' },
                el('div', { style: { fontWeight: 600 }, text: invitation.username }),
                el('div', { class: 'muted small', text: `${ROLE[invitation.role]} · ${formatDate(invitation.created_at)}` })),
            el('button', {
                class: 'btn btn-ghost btn-sm', type: 'button', text: 'Bekor qilish',
                onclick: () => run(() => api.projects.cancelInvitation(projectId, invitation.id), 'Taklif bekor qilindi'),
            })))
        : el('li', {}, emptyState("Kutilayotgan taklif yo'q", null, 'mail')));
}

async function load() {
    const [project, members] = await Promise.all([api.projects.get(projectId), api.projects.members(projectId)]);
    myRole = project.my_role;
    const isManager = ['owner', 'admin'].includes(myRole);
    renderMembers(members);
    $('#invite-card').classList.toggle('hidden', !isManager);
    $('#pending-card').classList.toggle('hidden', !isManager);
    if (isManager) renderPending(await api.projects.invitations(projectId));
}

$('#invite-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const { user, role } = formData(form);
    withLoading(form.querySelector('button[type=submit]'), async () => {
        try {
            await api.projects.invite(projectId, user.trim(), role);
            toast('Taklif yuborildi', 'success');
            form.reset();
            load();
        } catch (error) {
            showError(error);
        }
    });
});

initApp();
load().catch(showError);
