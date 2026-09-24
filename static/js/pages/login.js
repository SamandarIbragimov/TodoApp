import * as api from '../api.js';
import { $, formData, withLoading } from '../ui.js';

const form = $('#login-form');
const errorBox = $('#form-error');

/** Faqat shu saytdagi manzilga qaytaramiz (open redirect'dan himoya). */
function nextUrl() {
    const next = new URLSearchParams(window.location.search).get('next') || '/';
    return next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

form.addEventListener('submit', (event) => {
    event.preventDefault();
    const { username, password } = formData(form);
    if (!username || !password) {
        errorBox.textContent = 'Login va parolni kiriting.';
        errorBox.classList.remove('hidden');
        return;
    }
    withLoading(form.querySelector('button[type=submit]'), async () => {
        try {
            await api.auth.login(username.trim(), password);
            window.location.href = nextUrl();
        } catch (error) {
            errorBox.textContent = error.message;
            errorBox.classList.remove('hidden');
            form.password.value = '';
            form.password.focus();
        }
    });
});
