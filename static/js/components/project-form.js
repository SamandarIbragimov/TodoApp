import * as api from '../api.js';
import { el, field, formData, openModal, toast } from '../ui.js';

/** Loyiha yaratish (project yo'q) yoki tahrirlash modali. Saqlangan loyihani qaytaradi. */
export function openProjectForm(project = null) {
    return new Promise((resolve) => {
        const name = el('input', { class: 'input', name: 'name', required: true, maxlength: 150, value: project?.name || '', placeholder: 'Masalan: Diplom ishi' });
        const description = el('textarea', { class: 'textarea', name: 'description', maxlength: 2000, placeholder: 'Loyiha nima haqida? (ixtiyoriy)' });
        description.value = project?.description || '';

        openModal({
            title: project ? 'Loyihani tahrirlash' : 'Yangi loyiha',
            submitText: project ? 'Saqlash' : 'Yaratish',
            body: el('div', { class: 'stack' }, field('Nomi', name), field('Tavsif', description)),
            onSubmit: async (form) => {
                const data = formData(form);
                const saved = project ? await api.projects.update(project.id, data) : await api.projects.create(data);
                toast(project ? 'Loyiha yangilandi' : 'Loyiha yaratildi', 'success');
                resolve(saved);
            },
            onClose: () => resolve(null),
        });
    });
}
