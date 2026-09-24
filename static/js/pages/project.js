import * as api from '../api.js';
import { initApp, refreshSidebar } from '../app.js';
import { openProjectForm } from '../components/project-form.js';
import { createTaskView } from '../components/task-view.js';
import { $, clear, confirmDialog, icon, rolePill, showError, toast } from '../ui.js';

const projectId = JSON.parse($('#project-id').textContent);
$('main.content').dataset.projectId = projectId;

$('#new-task').prepend(icon('plus'));
$('#members-link').prepend(icon('users'));
$('#edit-project').prepend(icon('edit'));
$('#delete-project').prepend(icon('trash'));

function renderHeader(project) {
    $('#project-name').textContent = project.name;
    $('#project-description').textContent = project.description;
    clear($('#project-role'), rolePill(project.my_role));
    $('#members-link').append(` (${project.members_count})`);
    const isManager = ['owner', 'admin'].includes(project.my_role);
    $('#edit-project').classList.toggle('hidden', !isManager);
    $('#delete-project').classList.toggle('hidden', project.my_role !== 'owner');
}

async function main() {
    const [{ projects }, project] = await Promise.all([initApp(), api.projects.get(projectId)]);
    renderHeader(project);

    const view = createTaskView({
        root: $('#tasks'),
        projects,
        projectId,
        statsContainer: $('#stats'),
        defaultView: 'board',
    });
    $('#new-task').addEventListener('click', () => view.create());

    $('#edit-project').addEventListener('click', async () => {
        const saved = await openProjectForm(project);
        if (!saved) return;
        Object.assign(project, saved);
        $('#project-name').textContent = saved.name;
        $('#project-description').textContent = saved.description;
        document.title = `${saved.name} · Task Management`;
        refreshSidebar();
    });

    $('#delete-project').addEventListener('click', async () => {
        const ok = await confirmDialog(
            `"${project.name}" loyihasi va undagi barcha vazifalar o'chiriladi. Bu amalni qaytarib bo'lmaydi.`,
            { title: "Loyihani o'chirish" },
        );
        if (!ok) return;
        try {
            await api.projects.remove(projectId);
            toast("Loyiha o'chirildi", 'success');
            window.location.href = '/';
        } catch (error) {
            showError(error);
        }
    });
}

main().catch(showError);
