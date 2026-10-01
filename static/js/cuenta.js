const route = location.pathname;
const forms = {
    '/recuperar': document.getElementById('recoveryForm'),
    '/reenviar-verificacion': document.getElementById('resendForm'),
    '/confirmar-email': document.getElementById('verifyForm'),
    '/restablecer': document.getElementById('resetForm')
};
const copy = {
    '/recuperar': ['Restablecer contraseña', 'Te enviaremos un enlace si el correo corresponde a una cuenta.'],
    '/reenviar-verificacion': ['Verificar correo', 'Solicita un nuevo enlace de verificación.'],
    '/confirmar-email': ['Confirmar correo', 'Confirma que esta dirección de correo te pertenece.'],
    '/restablecer': ['Elegir contraseña nueva', 'Usa al menos 12 caracteres.']
};
const form = forms[route];
const status = document.getElementById('accountStatus');
const token = new URLSearchParams(location.hash.slice(1)).get('token') || '';
document.getElementById('accountTitle').textContent = copy[route]?.[0] || 'Seguridad de cuenta';
document.getElementById('accountDescription').textContent = copy[route]?.[1] || '';
if (form) form.hidden = false;
if ((route === '/confirmar-email' || route === '/restablecer') && !token) {
    status.textContent = 'Este enlace no es válido. Solicita uno nuevo para continuar.';
    form.querySelector('button').disabled = true;
}

function csrfToken() {
    const cookie = document.cookie.split('; ').find(item => item.startsWith('csrf_token='));
    return cookie ? decodeURIComponent(cookie.slice('csrf_token='.length)) : '';
}

if (form) {
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if ((route === '/confirmar-email' || route === '/restablecer') && !token) {
            status.textContent = 'El enlace no contiene un token válido. Solicita uno nuevo.';
            return;
        }

        const body = new FormData(form);
        if (route === '/confirmar-email' || route === '/restablecer') body.append('token', token);
        status.textContent = 'Procesando...';

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: { Accept: 'application/json', 'X-CSRF-Token': csrfToken() },
                body,
                credentials: 'same-origin'
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'No se pudo completar la operación');
            status.textContent = data.message;
        } catch (error) {
            status.textContent = error.message;
        }
    });
}