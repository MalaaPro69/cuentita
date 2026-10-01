from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pathlib import Path
from pydantic import EmailStr
from app.database.connection import get_db
from app.schemas.pydantic_schemas import UsuarioCreate, UsuarioResponse
from app.config import settings
from app.controllers import auth_controller

router = APIRouter(prefix="", tags=["Autenticación"])
FRONTEND_DIR = Path(__file__).resolve().parents[2]


def _frontend_file(name: str) -> str:
    return (FRONTEND_DIR / "templates" / name).read_text(encoding="utf-8")


def _auth_page(title: str, action: str, button_text: str, footer_link: str, footer_text: str, field_name: str = "username"):
    return _frontend_file("registro.html" if action == "/registro" else "login.html")
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cuentita | {title}</title>
        <style>
            :root {{
                --bg: #f5f7ff;
                --panel: #ffffff;
                --primary: #4f46e5;
                --primary-dark: #3730a3;
                --text: #1f2937;
                --muted: #6b7280;
                --border: #e5e7eb;
                --shadow: rgba(79, 70, 229, 0.15);
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
                font-family: Arial, sans-serif;
                color: var(--text);
            }}
            .card {{
                width: min(92vw, 420px);
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 20px;
                box-shadow: 0 18px 40px var(--shadow);
                padding: 32px 28px;
            }}
            .brand {{ text-align: center; margin-bottom: 20px; }}
            .brand h1 {{ margin: 0; font-size: 2rem; color: var(--primary); }}
            .brand p {{ margin: 8px 0 0; color: var(--muted); }}
            form {{ display: flex; flex-direction: column; gap: 16px; }}
            label {{ font-size: 0.92rem; font-weight: 600; color: var(--text); }}
            input {{
                width: 100%;
                margin-top: 8px;
                padding: 12px 14px;
                border: 1px solid var(--border);
                border-radius: 12px;
                font-size: 1rem;
                outline: none;
                transition: border-color 0.2s ease, box-shadow 0.2s ease;
            }}
            input:focus {{
                border-color: var(--primary);
                box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
            }}
            button {{
                border: none;
                border-radius: 12px;
                padding: 14px 16px;
                font-size: 1rem;
                font-weight: 700;
                cursor: pointer;
                color: white;
                background: linear-gradient(135deg, var(--primary), var(--primary-dark));
                box-shadow: 0 12px 24px rgba(79, 70, 229, 0.2);
            }}
            .footer {{ margin-top: 18px; text-align: center; color: var(--muted); font-size: 0.9rem; }}
            .footer a {{ color: var(--primary); text-decoration: none; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="brand">
                <h1>Cuentita</h1>
                <p>Gestiona tus gastos con claridad</p>
            </div>

            <form id="authForm" method="post" action="{action}">
                <div>
                    <label for="{field_name}">{'Usuario' if field_name == 'username' else 'Email'}</label>
                    <input id="{field_name}" name="{field_name}" type="email" placeholder="correo@ejemplo.com" required>
                </div>

                <div>
                    <label for="password">Contraseña</label>
                    <input id="password" name="password" type="password" placeholder="Tu contraseña" required>
                </div>

                <button type="submit">{button_text}</button>
            </form>

            <div id="authStatus" style="margin-top: 12px; color: #dc2626; min-height: 20px; font-size: 0.9rem;"></div>

            <div class="footer">
                {footer_text} <a href="{footer_link}">{'Iniciar sesión' if title == 'Crear cuenta' else 'Crear cuenta'}</a>
            </div>
        </div>

        <script>
            const authForm = document.getElementById('authForm');
            const authStatus = document.getElementById('authStatus');
            if (authForm) {{
                authForm.addEventListener('submit', async (event) => {{
                    event.preventDefault();
                    const form = event.currentTarget;
                    const isRegistration = form.action.endsWith('/registro');
                    authStatus.textContent = isRegistration ? 'Creando cuenta...' : 'Iniciando sesión...';

                    try {{
                        const csrfCookie = document.cookie.split('; ').find(item => item.startsWith('csrf_token='));
                        const csrfToken = csrfCookie ? decodeURIComponent(csrfCookie.slice('csrf_token='.length)) : '';
                        const response = await fetch(form.action, {{
                            method: 'POST',
                            headers: {{ Accept: 'application/json', 'X-CSRF-Token': csrfToken }},
                            body: new FormData(form)
                        }});

                        const data = await response.json();
                        if (!response.ok) {{
                            throw new Error(data.detail || 'Credenciales inválidas');
                        }}

                        authStatus.style.color = '#16a34a';
                        if (isRegistration) {{
                            authStatus.textContent = 'Cuenta creada. Redirigiendo al login...';
                            setTimeout(() => window.location.href = '/login', 600);
                        }} else {{
                            authStatus.textContent = 'Login correcto. Redirigiendo...';
                            setTimeout(() => window.location.href = '/menu', 600);
                        }}
                    }} catch (error) {{
                        authStatus.style.color = '#dc2626';
                        authStatus.textContent = error.message;
                    }}
                }});
            }}
        </script>
    </body>
    </html>
    """


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return _auth_page(
        title="Iniciar sesión",
        action="/login",
        button_text="Iniciar sesión",
        footer_link="/registro",
        footer_text="¿No tienes cuenta?",
        field_name="username"
    )


@router.get("/registro", response_class=HTMLResponse)
def register_page():
    return _auth_page(
        title="Crear cuenta",
        action="/registro",
        button_text="Registrarme",
        footer_link="/login",
        footer_text="¿Ya tienes cuenta?",
        field_name="email"
    )


@router.post("/registro")
def registrar(email: EmailStr = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    usuario = UsuarioCreate(email=email, password=password, nombre=email.split('@')[0])
    auth_controller.registrar_nuevo_usuario(usuario, db)
    return {"message": "Cuenta creada. Revisa tu correo para verificar la cuenta."}


@router.get("/recuperar", response_class=HTMLResponse)
@router.get("/reenviar-verificacion", response_class=HTMLResponse)
@router.get("/confirmar-email", response_class=HTMLResponse)
@router.get("/restablecer", response_class=HTMLResponse)
def cuenta_page():
    return _frontend_file("cuenta.html")


@router.post("/reenviar-verificacion")
def reenviar_verificacion(email: str = Form(...), db: Session = Depends(get_db)):
    auth_controller.reenviar_verificacion(email, db)
    return {"message": "Si la cuenta existe y aún no está verificada, enviaremos un nuevo enlace."}


@router.post("/solicitar-recuperacion")
def solicitar_recuperacion(email: str = Form(...), db: Session = Depends(get_db)):
    auth_controller.solicitar_recuperacion(email, db)
    return {"message": "Si existe una cuenta para ese correo, enviaremos instrucciones para restablecer la contraseña."}


@router.post("/confirmar-email")
def confirmar_email(token: str = Form(...), db: Session = Depends(get_db)):
    auth_controller.confirmar_email(token, db)
    return {"message": "Correo verificado. Ya puedes iniciar sesión."}


@router.post("/restablecer")
def restablecer_contrasena(token: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    auth_controller.restablecer_contrasena(token, password, db)
    return {"message": "Contraseña actualizada. Inicia sesión con la nueva contraseña."}


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return _frontend_file("dashboard.html")
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cuentita | Dashboard</title>
        <style>
            :root {
                --bg: #eef2ff;
                --panel: #ffffff;
                --primary: #4f46e5;
                --primary-dark: #3730a3;
                --text: #1f2937;
                --muted: #64748b;
                --success: #16a34a;
                --danger: #dc2626;
                --border: #e5e7eb;
            }
            * { box-sizing: border-box; }
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
                color: var(--text);
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 32px 20px 60px;
            }
            .topbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }
            .brand {
                font-size: 2rem;
                font-weight: 700;
                color: var(--primary);
            }
            .logout-btn {
                border: none;
                background: var(--primary);
                color: white;
                border-radius: 10px;
                padding: 10px 16px;
                cursor: pointer;
                font-weight: 700;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 18px;
                margin-bottom: 26px;
            }
            .card {
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 20px;
                box-shadow: 0 12px 24px rgba(79,70,229,.08);
            }
            .label {
                color: var(--muted);
                font-size: 0.9rem;
                margin-bottom: 8px;
            }
            .value {
                font-size: 1.8rem;
                font-weight: 700;
            }
            .forms {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 24px;
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            input, select, textarea, button {
                font: inherit;
            }
            input, select, textarea {
                width: 100%;
                padding: 12px 14px;
                border: 1px solid var(--border);
                border-radius: 12px;
                background: white;
            }
            button {
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                background: linear-gradient(135deg, var(--primary), var(--primary-dark));
                color: white;
                font-weight: 700;
                cursor: pointer;
            }
            .list {
                background: white;
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 18px;
            }
            .expense-toolbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
                margin-bottom: 16px;
            }
            .expense-toolbar h3 {
                margin: 0;
            }
            .expense-filter {
                width: min(100%, 220px);
                margin: 0;
            }
            .expense-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
                gap: 14px;
            }
            .expense-item {
                display: flex;
                flex-direction: column;
                gap: 10px;
                min-height: 150px;
                padding: 16px;
                border: 1px solid var(--border);
                border-radius: 14px;
                background: #fbfdff;
            }
            .expense-head {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 12px;
            }
            .expense-description {
                margin: 0;
                font-weight: 700;
                overflow-wrap: anywhere;
            }
            .expense-amount {
                color: var(--primary-dark);
                font-size: 1.05rem;
                font-weight: 700;
                white-space: nowrap;
            }
            .expense-meta {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                color: var(--muted);
                font-size: 0.88rem;
            }
            .category-tag {
                color: var(--primary-dark);
                font-weight: 700;
            }
            .delete-btn {
                margin-top: auto;
                padding: 9px 12px;
                background: #fff1f2;
                color: var(--danger);
                border: 1px solid #fecdd3;
                box-shadow: none;
            }
            .empty-state {
                grid-column: 1 / -1;
                padding: 26px;
                border: 1px dashed var(--border);
                border-radius: 14px;
                color: var(--muted);
                text-align: center;
            }
            .status {
                min-height: 24px;
                font-size: 0.9rem;
                margin-top: 8px;
            }
            .success { color: var(--success); }
            .error { color: var(--danger); }
            .notice { color: var(--muted); }
            .budget-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 12px;
                margin-top: 16px;
            }
            .budget-item {
                display: grid;
                gap: 10px;
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 16px;
                background: #fff;
            }
            .budget-head, .budget-details {
                display: flex;
                justify-content: space-between;
                gap: 12px;
            }
            .budget-head { font-weight: 700; }
            .budget-details, .budget-note { color: var(--muted); font-size: .9rem; }
            .budget-progress {
                height: 10px;
                overflow: hidden;
                border-radius: 999px;
                background: #e9edf5;
            }
            .budget-progress span {
                display: block;
                height: 100%;
                border-radius: inherit;
                background: var(--success);
            }
            .budget-item.near .budget-progress span { background: #d97706; }
            .budget-item.exceeded .budget-progress span { background: var(--danger); }
            .budget-delete {
                justify-self: start;
                padding: 7px 10px;
                background: #fff1f2;
                color: var(--danger);
                border: 1px solid #fecdd3;
                box-shadow: none;
            }
            #presupuestoForm {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                align-items: end;
                margin-bottom: 0;
            }
            .chart-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 24px 0;
            }
            .chart-card {
                background: white;
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 20px;
            }
            canvas {
                width: 100% !important;
                max-height: 300px;
            }
            @media (max-width: 700px) {
                .forms, .chart-grid { grid-template-columns: 1fr; }
                #presupuestoForm { grid-template-columns: 1fr; }
                .expense-toolbar { align-items: stretch; flex-direction: column; }
                .expense-filter { width: 100%; }
            }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="container">
            <div class="topbar">
                <div class="brand">Cuentita</div>
                <div style="display:flex; gap:8px; align-items:center;">
                    <a href="/menu" style="color:var(--primary); font-weight:700; text-decoration:none;">Menú principal</a>
                    <button class="logout-btn" onclick="logout()">Cerrar sesión</button>
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <div class="label">Total del mes</div>
                    <div id="totalMes" class="value">$0</div>
                </div>
                <div class="card">
                    <div class="label">Gastos registrados</div>
                    <div id="cantidadGastos" class="value">0</div>
                </div>
                <div class="card">
                    <div class="label">Categoría mayor</div>
                    <div id="categoriaMayor" class="value">-</div>
                </div>
            </div>

            <div class="forms">
                <div class="card">
                    <h3>Agregar gasto manual</h3>
                    <form id="gastoForm">
                        <input type="number" id="monto" step="0.01" placeholder="Monto" required>
                        <input type="text" id="descripcion" placeholder="Descripción" required>
                        <select id="categoria">
                            <option value="Alimentación">Alimentación</option>
                            <option value="Transporte">Transporte</option>
                            <option value="Servicios">Servicios</option>
                            <option value="Entretenimiento">Entretenimiento</option>
                            <option value="Salud">Salud</option>
                            <option value="Compras">Compras</option>
                            <option value="General">General</option>
                        </select>
                        <button type="submit">Guardar gasto</button>
                    </form>
                    <div id="manualStatus" class="status"></div>
                </div>

                <div class="card">
                    <h3>Analizar con IA</h3>
                    <form id="iaForm">
                        <textarea id="mensaje" rows="5" maxlength="2000" placeholder="Ej: Compré nafta por 1800 y comida por 650" required></textarea>
                        <button type="submit">Procesar con Gemini</button>
                    </form>
                    <div id="iaStatus" class="status"></div>
                </div>
            </div>

            <section class="card">
                <h3>Presupuestos mensuales (opcional)</h3>
                <p class="budget-note">Define solo los límites que te sirvan. Son avisos visuales al llegar al 80% y al superar el límite; nunca bloquean tus gastos. Puedes modificarlos o quitarlos cuando quieras.</p>
                <form id="presupuestoForm" class="forms">
                    <select id="presupuestoCategoria" aria-label="Categoría del presupuesto">
                        <option value="Alimentación">Alimentación</option>
                        <option value="Transporte">Transporte</option>
                        <option value="Servicios">Servicios</option>
                        <option value="Entretenimiento">Entretenimiento</option>
                        <option value="Salud">Salud</option>
                        <option value="Compras">Compras</option>
                        <option value="General">General</option>
                    </select>
                    <input type="number" id="presupuestoMonto" min="0.01" step="0.01" placeholder="Límite mensual" required>
                    <button type="submit">Guardar presupuesto</button>
                </form>
                <div id="presupuestoStatus" class="status" aria-live="polite"></div>
                <div id="presupuestosLista" class="budget-grid"></div>
            </section>

            <div class="chart-grid">
                <div class="chart-card">
                    <h3>Gastado por categoría</h3>
                    <canvas id="categoryChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Evolución mensual</h3>
                    <canvas id="trendChart"></canvas>
                </div>
            </div>

            <div class="card">
                <div class="expense-toolbar">
                    <h3>Listado de gastos</h3>
                    <select id="filtroCategoria" class="expense-filter" aria-label="Filtrar gastos por categoría">
                        <option value="Todas">Todas las categorías</option>
                    </select>
                </div>
                <div class="list">
                    <div id="tablaGastos" class="expense-grid"></div>
                </div>
            </div>
        </div>

        <script>
            let categoryChart;
            let trendChart;
            let gastosActuales = [];
            let presupuestosActuales = [];

            function apiFetch(url, options = {}) {
                const csrfCookie = document.cookie.split('; ').find(item => item.startsWith('csrf_token='));
                const headers = {
                    'Accept': 'application/json',
                    'X-CSRF-Token': csrfCookie ? decodeURIComponent(csrfCookie.slice('csrf_token='.length)) : '',
                    ...(options.headers || {})
                };
                if (options.body && !(options.body instanceof FormData)) {
                    headers['Content-Type'] = 'application/json';
                }
                return fetch(url, { ...options, credentials: 'same-origin', headers });
            }

            function money(value) {
                return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(Number(value || 0));
            }

            async function logout() {
                const csrfCookie = document.cookie.split('; ').find(item => item.startsWith('csrf_token='));
                const csrfToken = csrfCookie ? decodeURIComponent(csrfCookie.slice('csrf_token='.length)) : '';
                await fetch('/logout', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken } });
                window.location.href = '/login';
            }

            function renderCategoryChart(data) {
                const labels = data.map(item => item.categoria);
                const values = data.map(item => Number(item.total || 0));
                const colors = ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#38bdf8', '#f97316'];

                if (categoryChart) categoryChart.destroy();
                categoryChart = new Chart(document.getElementById('categoryChart'), {
                    type: 'doughnut',
                    data: {
                        labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors.slice(0, labels.length),
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
            }

            function renderTrendChart(data) {
                const monthMap = {};
                for (const gasto of data) {
                    const fecha = new Date(gasto.fecha);
                    const monthKey = `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}`;
                    const label = fecha.toLocaleDateString('es-AR', { month: 'short', year: '2-digit' });
                    monthMap[monthKey] = (monthMap[monthKey] || 0) + Number(gasto.monto || 0);
                }

                const labels = Object.keys(monthMap).sort();
                const values = labels.map(key => monthMap[key]);
                const formattedLabels = labels.map(key => {
                    const [year, month] = key.split('-');
                    return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString('es-AR', { month: 'short', year: '2-digit' });
                });

                if (trendChart) trendChart.destroy();
                trendChart = new Chart(document.getElementById('trendChart'), {
                    type: 'bar',
                    data: {
                        labels: formattedLabels,
                        datasets: [{
                            label: 'Gasto total',
                            data: values,
                            backgroundColor: '#4f46e5'
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true, ticks: { callback: value => money(value) } }
                        }
                    }
                });
            }

            async function cargarResumen() {
                const [resumenRes, gastosRes] = await Promise.all([
                    apiFetch('/gastos/resumen-categorias'),
                    apiFetch('/gastos')
                ]);

                if (!resumenRes.ok || !gastosRes.ok) throw new Error('No se pudo cargar resumen');

                const resumen = await resumenRes.json();
                const gastos = await gastosRes.json();

                let total = 0;
                for (const item of resumen) total += Number(item.total || 0);
                document.getElementById('totalMes').textContent = money(total);
                document.getElementById('cantidadGastos').textContent = gastos.length;
                const mayor = resumen.length ? resumen.reduce((a, b) => Number(a.total) > Number(b.total) ? a : b) : null;
                document.getElementById('categoriaMayor').textContent = mayor ? mayor.categoria : '-';

                renderCategoryChart(resumen);
                renderTrendChart(gastos);
            }

            async function cargarGastos() {
                const res = await apiFetch('/gastos');
                if (!res.ok) throw new Error('No se pudo cargar gastos');
                gastosActuales = await res.json();
                actualizarFiltroCategorias();
                renderGastos();
            }

            function renderPresupuestos() {
                const container = document.getElementById('presupuestosLista');
                container.replaceChildren();
                if (!presupuestosActuales.length) {
                    const empty = document.createElement('div');
                    empty.className = 'empty-state';
                    empty.textContent = 'No configuraste presupuestos. Si quieres, agrega alguno arriba.';
                    container.appendChild(empty);
                    return;
                }

                for (const presupuesto of presupuestosActuales) {
                    const item = document.createElement('article');
                    item.className = `budget-item ${presupuesto.estado === 'cerca' ? 'near' : presupuesto.estado === 'superado' ? 'exceeded' : ''}`;
                    const head = document.createElement('div');
                    head.className = 'budget-head';
                    const category = document.createElement('span');
                    category.textContent = presupuesto.categoria;
                    const threshold = document.createElement('span');
                    threshold.textContent = money(presupuesto.monto_maximo);
                    head.append(category, threshold);

                    const progress = document.createElement('div');
                    progress.className = 'budget-progress';
                    progress.setAttribute('role', 'progressbar');
                    progress.setAttribute('aria-valuemin', '0');
                    progress.setAttribute('aria-valuemax', '100');
                    progress.setAttribute('aria-valuenow', String(Math.min(100, Math.round(presupuesto.porcentaje))));
                    const fill = document.createElement('span');
                    fill.style.width = `${Math.min(100, Math.max(0, presupuesto.porcentaje))}%`;
                    progress.appendChild(fill);

                    const details = document.createElement('div');
                    details.className = 'budget-details';
                    const spent = document.createElement('span');
                    spent.textContent = `${money(presupuesto.gastado)} gastados`;
                    const percentage = document.createElement('span');
                    percentage.textContent = `${Math.round(presupuesto.porcentaje)}%`;
                    details.append(spent, percentage);

                    const note = document.createElement('div');
                    note.className = 'budget-note';
                    note.textContent = presupuesto.estado === 'superado'
                        ? 'Superaste este límite mensual.'
                        : presupuesto.estado === 'cerca'
                            ? 'Ya usaste al menos el 80% del límite.'
                            : 'Dentro del límite mensual.';

                    const remove = document.createElement('button');
                    remove.className = 'budget-delete';
                    remove.type = 'button';
                    remove.textContent = 'Quitar presupuesto';
                    remove.addEventListener('click', () => eliminarPresupuesto(presupuesto.id));
                    item.append(head, progress, details, note, remove);
                    container.appendChild(item);
                }
            }

            async function cargarPresupuestos() {
                const response = await apiFetch('/api/presupuestos');
                if (!response.ok) throw new Error('No se pudieron cargar los presupuestos.');
                presupuestosActuales = await response.json();
                renderPresupuestos();
            }

            document.getElementById('presupuestoForm').addEventListener('submit', async (event) => {
                event.preventDefault();
                const category = document.getElementById('presupuestoCategoria').value;
                const amount = Number(document.getElementById('presupuestoMonto').value);
                const status = document.getElementById('presupuestoStatus');
                const existing = presupuestosActuales.find(item => item.categoria === category);
                status.className = 'status';
                status.textContent = 'Guardando presupuesto...';

                try {
                    const response = await apiFetch(
                        existing ? `/api/presupuestos/${existing.id}` : '/api/presupuestos',
                        {
                            method: existing ? 'PUT' : 'POST',
                            body: JSON.stringify({ categoria: category, monto_maximo: amount })
                        }
                    );
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'No se pudo guardar el presupuesto.');
                    }
                    document.getElementById('presupuestoForm').reset();
                    status.textContent = 'Presupuesto guardado. Puedes cambiarlo o quitarlo cuando quieras.';
                    status.classList.add('success');
                    await cargarPresupuestos();
                } catch (error) {
                    status.textContent = error.message;
                    status.classList.add('error');
                }
            });

            async function eliminarPresupuesto(id) {
                const status = document.getElementById('presupuestoStatus');
                try {
                    const response = await apiFetch(`/api/presupuestos/${id}`, { method: 'DELETE' });
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'No se pudo quitar el presupuesto.');
                    }
                    status.className = 'status success';
                    status.textContent = 'Presupuesto quitado.';
                    await cargarPresupuestos();
                } catch (error) {
                    status.className = 'status error';
                    status.textContent = error.message;
                }
            }

            function actualizarFiltroCategorias() {
                const filtro = document.getElementById('filtroCategoria');
                const seleccionActual = filtro.value;
                const categorias = [...new Set(
                    gastosActuales.map(gasto => gasto.categoria || 'General')
                )].sort((a, b) => a.localeCompare(b, 'es'));

                filtro.innerHTML = '<option value="Todas">Todas las categorías</option>';
                for (const categoria of categorias) {
                    const option = document.createElement('option');
                    option.value = categoria;
                    option.textContent = categoria;
                    filtro.appendChild(option);
                }

                filtro.value = categorias.includes(seleccionActual) ? seleccionActual : 'Todas';
            }

            function renderGastos() {
                const container = document.getElementById('tablaGastos');
                const categoria = document.getElementById('filtroCategoria').value;
                const gastos = categoria === 'Todas'
                    ? gastosActuales
                    : gastosActuales.filter(gasto => (gasto.categoria || 'General') === categoria);
                container.innerHTML = '';

                if (!gastos.length) {
                    const empty = document.createElement('div');
                    empty.className = 'empty-state';
                    empty.textContent = categoria === 'Todas'
                        ? 'No hay gastos registrados.'
                        : 'No hay gastos en esta categoría.';
                    container.appendChild(empty);
                    return;
                }

                for (const gasto of gastos) {
                    const card = document.createElement('article');
                    card.className = 'expense-item';

                    const head = document.createElement('div');
                    head.className = 'expense-head';
                    const description = document.createElement('p');
                    description.className = 'expense-description';
                    description.textContent = gasto.descripcion;
                    const amount = document.createElement('span');
                    amount.className = 'expense-amount';
                    amount.textContent = money(gasto.monto);
                    head.append(description, amount);

                    const meta = document.createElement('div');
                    meta.className = 'expense-meta';
                    const date = document.createElement('span');
                    date.textContent = new Date(gasto.fecha).toLocaleDateString('es-AR');
                    const tag = document.createElement('span');
                    tag.className = 'category-tag';
                    tag.textContent = gasto.categoria || 'General';
                    meta.append(date, tag);

                    const deleteButton = document.createElement('button');
                    deleteButton.className = 'delete-btn';
                    deleteButton.type = 'button';
                    deleteButton.textContent = 'Eliminar';
                    deleteButton.addEventListener('click', () => eliminarGasto(gasto.id));

                    card.append(head, meta, deleteButton);
                    container.appendChild(card);
                }
            }

            async function eliminarGasto(id) {
                const res = await apiFetch(`/gastos/${id}`, { method: 'DELETE' });
                if (!res.ok) {
                    alert('No se pudo eliminar el gasto');
                    return;
                }
                await cargarResumen();
                await cargarGastos();
                await cargarPresupuestos();
            }

            document.getElementById('gastoForm').addEventListener('submit', async (event) => {
                event.preventDefault();
                const monto = Number(document.getElementById('monto').value);
                const descripcion = document.getElementById('descripcion').value.trim();
                const categoria = document.getElementById('categoria').value;
                const status = document.getElementById('manualStatus');
                status.textContent = 'Guardando...';
                status.className = 'status';

                try {
                    const res = await apiFetch('/gastos', {
                        method: 'POST',
                        body: JSON.stringify({ monto, descripcion, categoria })
                    });
                    if (!res.ok) {
                        const error = await res.json();
                        throw new Error(error.detail || 'Error al guardar');
                    }
                    status.textContent = 'Gasto guardado correctamente.';
                    status.classList.add('success');
                    document.getElementById('gastoForm').reset();
                    await cargarResumen();
                    await cargarGastos();
                    await cargarPresupuestos();
                } catch (err) {
                    status.textContent = err.message;
                    status.classList.add('error');
                }
            });

            document.getElementById('filtroCategoria').addEventListener('change', renderGastos);

            document.getElementById('iaForm').addEventListener('submit', async (event) => {
                event.preventDefault();
                const mensaje = document.getElementById('mensaje').value.trim();
                const status = document.getElementById('iaStatus');
                status.textContent = 'Procesando con IA...';
                status.className = 'status';

                try {
                    const res = await apiFetch('/chat/procesar', {
                        method: 'POST',
                        body: JSON.stringify({ mensaje })
                    });
                    if (!res.ok) {
                        const error = await res.json();
                        throw new Error(error.detail || 'Error al procesar');
                    }
                    const resultado = await res.json();
                    if (!resultado.es_gasto) {
                        status.textContent = resultado.respuesta_chat;
                        status.classList.add('notice');
                        return;
                    }
                    const gasto = resultado.gasto;
                    status.textContent = `Gasto registrado: ${gasto.descripcion} (${money(gasto.monto)})`;
                    status.classList.add('success');
                    document.getElementById('iaForm').reset();
                    await cargarResumen();
                    await cargarGastos();
                    await cargarPresupuestos();
                } catch (err) {
                    status.textContent = err.message;
                    status.classList.add('error');
                }
            });

            async function init() {
                try {
                    await cargarResumen();
                    await cargarGastos();
                    await cargarPresupuestos();
                } catch (err) {
                    document.getElementById('totalMes').textContent = 'Error';
                    document.getElementById('categoriaMayor').textContent = '-';
                    document.getElementById('tablaGastos').textContent = 'Error al cargar los gastos.';
                }
            }

            init();
        </script>
    </body>
    </html>
    """


@router.get("/planificacion", response_class=HTMLResponse)
def planning_page():
    return _frontend_file("planificacion.html")


@router.get("/menu", response_class=HTMLResponse)
def menu_page():
    return _frontend_file("menu.html")
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cuentita | Menú principal</title>
        <style>
            :root { --ink:#172033; --muted:#667085; --line:#dfe5ef; --accent:#4f46e5; --dark:#3730a3; }
            * { box-sizing:border-box; }
            body { margin:0; min-height:100vh; color:var(--ink); font-family:Arial,sans-serif; background:linear-gradient(135deg,#eef2ff,#fbfcff); }
            .wrap { width:min(1100px,92vw); margin:auto; padding:40px 0 60px; }
            header { display:flex; justify-content:space-between; align-items:center; gap:18px; margin-bottom:48px; }
            .brand { color:var(--accent); font-size:2rem; font-weight:800; }
            button { border:0; border-radius:10px; padding:11px 16px; background:var(--accent); color:white; font-weight:700; cursor:pointer; }
            h1 { max-width:650px; font-size:clamp(2rem,5vw,3.8rem); line-height:1.05; margin:0 0 14px; }
            .lead { max-width:620px; color:var(--muted); font-size:1.1rem; margin:0 0 32px; }
            .menu-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
            .menu-card { display:flex; min-height:220px; flex-direction:column; justify-content:space-between; padding:24px; border:1px solid var(--line); border-radius:18px; background:white; box-shadow:0 14px 30px #4f46e512; text-decoration:none; color:var(--ink); transition:transform .18s ease, box-shadow .18s ease; }
            .menu-card:hover { transform:translateY(-4px); box-shadow:0 18px 36px #4f46e526; }
            .icon { font-size:2rem; }
            .menu-card h2 { margin:18px 0 8px; }
            .menu-card p { color:var(--muted); line-height:1.45; margin:0; }
            .open { margin-top:20px; color:var(--accent); font-weight:800; }
            @media(max-width:760px) { header { align-items:flex-start; flex-direction:column; margin-bottom:34px; } .menu-grid { grid-template-columns:1fr; } .menu-card { min-height:180px; } }
        </style>
    </head>
    <body><main class="wrap">
        <header><div class="brand">Cuentita</div><button onclick="logout()">Cerrar sesión</button></header>
        <h1>¿Qué querés revisar hoy?</h1>
        <p class="lead">Organizá tus movimientos en un solo lugar y mirá cómo evoluciona tu dinero.</p>
        <section class="menu-grid">
            <a class="menu-card" href="/dashboard"><div><div class="icon">↘</div><h2>Gastos</h2><p>Registrá consumos manualmente o con ayuda de la IA y analizá tus categorías.</p></div><div class="open">Abrir gastos →</div></a>
            <a class="menu-card" href="/ingresos"><div><div class="icon">↗</div><h2>Ingresos</h2><p>Anotá el dinero que entra y el motivo para conocer tu balance real.</p></div><div class="open">Abrir ingresos →</div></a>
            <a class="menu-card" href="/inversiones"><div><div class="icon">◒</div><h2>Inversiones</h2><p>Guardá tus activos, capital invertido y rendimiento estimado.</p></div><div class="open">Abrir inversiones →</div></a>
        </section>
    </main><script>async function logout(){const cookie=document.cookie.split('; ').find(item=>item.startsWith('csrf_token='));const token=cookie?decodeURIComponent(cookie.slice('csrf_token='.length)):'';await fetch('/logout',{method:'POST',headers:{'X-CSRF-Token':token}});location.href='/login';}</script></body></html>
    """


@router.post("/login")
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ip_address = auth_controller.get_client_ip(request)
    token_data = auth_controller.autenticar_usuario(form_data.username, form_data.password, db, ip_address)
    response.set_cookie(
        key="access_token",
        value=token_data["access_token"],
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        path="/",
    )
    return {"message": "Inicio de sesión correcto"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        path="/",
    )
    return {"message": "Sesión cerrada"}