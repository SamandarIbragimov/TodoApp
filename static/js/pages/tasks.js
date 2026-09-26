import { initApp } from '../app.js';
import { createTaskView } from '../components/task-view.js';
import { $, icon } from '../ui.js';

$('#new-task').prepend(icon('plus'));

initApp().then(({ projects }) => {
    const view = createTaskView({ root: $('#tasks'), projects, statsContainer: $('#stats') });
    $('#new-task').addEventListener('click', () => view.create());
});
