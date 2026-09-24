import * as api from '../api.js';
import { initApp } from '../app.js';
import { $, avatar, clear, confirmDialog, el, field, formatDate, formData, icon, openModal, showError, toast, withLoading } from '../ui.js';

const MAX_AVATAR = 2 * 1024 * 1024;
const form = $('#profile-form');

function renderProfile(profile) {
    clear($('#avatar-preview'), avatar(profile.username, { size: 'lg', src: profile.avatar }));
    $('#profile-username').textContent = profile.username;
    $('#avatar-remove').classList.toggle('hidden', !profile.avatar);
    form.first_name.value = profile.first_name;
    form.last_name.value = profile.last_name;
    form.email.value = profile.email;
    $('#joined').textContent = profile.created_at ? `Ro'yxatdan o'tgan: ${formatDate(profile.created_at)}` : '';
}

form.addEventListener('submit', (event) => {
    event.preventDefault();
    withLoading(form.querySelector('button[type=submit]'), async () => {
        try {
            renderProfile(await api.auth.updateProfile(formData(form)));
            toast('Profil saqlandi', 'success');
        } catch (error) {
            showError(error);
        }
    });
});

$('#avatar-input').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    event.target.value = '';
    if (!file) return;
    if (file.size > MAX_AVATAR) {
        showError(new Error('Rasm hajmi 2 MB dan oshmasligi kerak.'));
        return;
    }
    const data = new FormData();
    data.append('avatar', file);
    try {
        renderProfile(await api.auth.updateProfile(data));
        toast('Rasm yangilandi', 'success');
        window.location.reload(); // yon paneldagi avatar ham yangilansin
    } catch (error) {
        showError(error);
    }
});

$('#avatar-remove').addEventListener('click', async () => {
    try {
        renderProfile(await api.auth.updateProfile({ avatar: null }));
        window.location.reload();
    } catch (error) {
        showError(error);
    }
});

// ---------- Teglar ----------
async function loadTags() {
    const tags = await api.tags.list();
    clear($('#tag-list'), tags.length
        ? tags.map((tag) => el('span', { class: 'chip', style: { height: '28px' } },
            el('span', { class: 'swatch', style: { background: tag.color } }),
            tag.name,
            el('button', { type: 'button', title: 'Tahrirlash', onclick: () => editTag(tag) }, icon('edit', 12)),
            el('button', { type: 'button', title: "O'chirish", onclick: () => deleteTag(tag) }, icon('x', 12))))
        : el('span', { class: 'muted small', text: "Hozircha teg yo'q" }));
}

function editTag(tag) {
    const name = el('input', { class: 'input', name: 'name', required: true, maxlength: 50, value: tag.name });
    const color = el('input', { type: 'color', name: 'color', value: tag.color, style: { width: '48px', height: '38px', border: 0, background: 'none' } });
    openModal({
        title: 'Tegni tahrirlash',
        body: el('div', { class: 'stack' }, field('Nomi', name), field('Rangi', color)),
        onSubmit: async () => {
            await api.tags.update(tag.id, { name: name.value.trim(), color: color.value });
            loadTags();
        },
    });
}

async function deleteTag(tag) {
    if (!(await confirmDialog(`"${tag.name}" tegi o'chiriladi va barcha vazifalardan olib tashlanadi.`))) return;
    try {
        await api.tags.remove(tag.id);
        loadTags();
    } catch (error) {
        showError(error);
    }
}

$('#tag-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const tagForm = event.currentTarget;
    withLoading(tagForm.querySelector('button'), async () => {
        try {
            const { name, color } = formData(tagForm);
            await api.tags.create({ name: name.trim(), color });
            tagForm.name.value = '';
            loadTags();
        } catch (error) {
            showError(error);
        }
    });
});

initApp();
api.auth.profile().then(renderProfile).catch(showError);
loadTags().catch(showError);
