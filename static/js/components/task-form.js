import * as api from '../api.js';
import { clear, currentUser, el, field, openModal, PRIORITY, select, STATUS, toast } from '../ui.js';

const MANAGER_ROLES = ['owner', 'admin'];
const membersCache = new Map();

async function loadMembers(projectId) {
    if (!membersCache.has(projectId)) membersCache.set(projectId, api.projects.members(projectId));
    return membersCache.get(projectId);
}

/**
 * Task yaratish/tahrirlash modali.
 * @param {object} options
 * @param {object} [options.task]       tahrirlanadigan task (bo'lmasa — yangi)
 * @param {number} [options.projectId]  loyiha oldindan tanlangan (loyiha sahifasida)
 * @param {Array}  options.projects     foydalanuvchi loyihalari (my_role bilan)
 * @param {object} [options.defaults]   yangi task uchun boshlang'ich qiymatlar (masalan status)
 * @returns {Promise<object|null>} saqlangan task
 */
export async function openTaskForm({ task = null, projectId = null, projects = [], defaults = {} }) {
    const myTags = await api.tags.list();
    const initialProject = task ? task.project : projectId;

    const title = el('input', { class: 'input', name: 'title', required: true, maxlength: 200, value: task?.title || '', placeholder: 'Nima qilish kerak?' });
    const description = el('textarea', { class: 'textarea', name: 'description', placeholder: "Batafsil ma'lumot (ixtiyoriy)" });
    description.value = task?.description || '';
    const status = select('status', Object.entries(STATUS), task?.status || defaults.status || 'todo');
    const priority = select('priority', Object.entries(PRIORITY), task?.priority || 'medium');
    const dueDate = el('input', { class: 'input', type: 'date', name: 'due_date', value: task?.due_date || '' });
    const project = select(
        'project',
        [['', 'Shaxsiy (loyihasiz)'], ...projects.map((p) => [p.id, p.name])],
        initialProject,
        // Taskni boshqa loyihaga ko'chirib bo'lmaydi (backend qoidasi)
        { disabled: Boolean(task || projectId) },
    );
    const assignee = el('select', { class: 'select', name: 'assigned_to' });

    async function renderAssignees() {
        const selectedProject = project.value ? Number(project.value) : null;
        const current = task?.assigned_to ?? (defaults.assigned_to || '');
        let options = [['', 'Tayinlanmagan'], [currentUser.id, `Men (${currentUser.username})`]];

        if (selectedProject) {
            const role = projects.find((p) => p.id === selectedProject)?.my_role;
            const members = await loadMembers(selectedProject);
            if (MANAGER_ROLES.includes(role)) {
                options = [['', 'Tayinlanmagan'], ...members.map((m) => [m.user_id, m.user_id === currentUser.id ? `Men (${m.username})` : m.username])];
            }
        }
        // Hozirgi mas'ul ro'yxatda bo'lmasa ham ko'rinib tursin (o'zgartirilmasa saqlanadi)
        if (task?.assigned_to && !options.some(([id]) => String(id) === String(task.assigned_to))) {
            options.push([task.assigned_to, task.assigned_to_username]);
        }
        clear(assignee, options.map(([id, label]) => el('option', { value: id, text: label, selected: String(id) === String(current) })));
    }
    project.addEventListener('change', renderAssignees);
    await renderAssignees();

    // Teglar: o'zimniki tanlanadi, boshqa a'zolar qo'ygan teglar saqlanib qoladi
    const selectedTagIds = new Set(task?.tags || []);
    const myTagIds = new Set(myTags.map((t) => t.id));
    const foreignTags = (task?.tags_detail || []).filter((t) => !myTagIds.has(t.id));
    const tagBoxes = myTags.map((tag) =>
        el('label', { class: 'chip', style: { cursor: 'pointer', height: '28px' } },
            el('input', { type: 'checkbox', value: tag.id, checked: selectedTagIds.has(tag.id), style: { accentColor: tag.color } }),
            el('span', { class: 'swatch', style: { background: tag.color } }),
            tag.name));
    const tagsField = el('div', { class: 'field full' },
        el('span', { class: 'label', text: 'Teglar' }),
        myTags.length || foreignTags.length
            ? el('div', { class: 'row wrap' }, tagBoxes, foreignTags.map((tag) =>
                el('span', { class: 'chip', title: "Boshqa a'zoning tegi" }, el('span', { class: 'swatch', style: { background: tag.color } }), tag.name)))
            : el('div', { class: 'hint' }, "Teglar yo'q. ", el('a', { href: '/accounts/profile/#tags', text: 'Profil sahifasida yarating' })));

    const body = el('div', { class: 'form-grid' },
        el('div', { class: 'full' }, field('Nomi', title)),
        el('div', { class: 'full' }, field('Tavsif', description)),
        field('Holati', status),
        field('Muhimligi', priority),
        field('Muddat', dueDate),
        field('Loyiha', project),
        el('div', { class: 'full' }, field("Mas'ul", assignee)),
        tagsField);

    return new Promise((resolve) => {
        openModal({
            title: task ? 'Vazifani tahrirlash' : 'Yangi vazifa',
            submitText: task ? 'Saqlash' : "Qo'shish",
            body,
            onSubmit: async () => {
                const payload = {
                    title: title.value.trim(),
                    description: description.value.trim(),
                    status: status.value,
                    priority: priority.value,
                    due_date: dueDate.value || null,
                    assigned_to: assignee.value ? Number(assignee.value) : null,
                    tags: [
                        ...tagBoxes.filter((box) => box.querySelector('input').checked).map((box) => Number(box.querySelector('input').value)),
                        ...foreignTags.map((t) => t.id),
                    ],
                };
                if (!task) payload.project = project.value ? Number(project.value) : null;
                const saved = task ? await api.tasks.update(task.id, payload) : await api.tasks.create(payload);
                toast(task ? 'Vazifa saqlandi' : "Vazifa qo'shildi", 'success');
                resolve(saved);
            },
            onClose: () => resolve(null),
        });
    });
}
