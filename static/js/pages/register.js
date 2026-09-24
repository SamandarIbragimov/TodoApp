import * as api from '../api.js';
import { $, formData, withLoading } from '../ui.js';

const form = $('#register-form');
const errorBox = $('#form-error');

function showErrors(error) {
    let fieldErrors = false;
    form.querySelectorAll('[data-error]').forEach((node) => {
        node.textContent = error ? error.field(node.dataset.error) : '';
        fieldErrors ||= Boolean(node.textContent);
    });
    // Maydonga tegishli bo'lmagan xatolar (masalan, juda ko'p urinish) umumiy blokda
    errorBox.textContent = error && !fieldErrors ? error.message : '';
    errorBox.classList.toggle('hidden', !errorBox.textContent);
}

form.addEventListener('submit', (event) => {
    event.preventDefault();
    const data = formData(form);
    showErrors(null);
    withLoading(form.querySelector('button[type=submit]'), async () => {
        try {
            await api.auth.register({ ...data, username: data.username.trim(), email: data.email.trim() });
            await api.auth.login(data.username.trim(), data.password);
            window.location.href = '/';
        } catch (error) {
            showErrors(error);
        }
    });
});
