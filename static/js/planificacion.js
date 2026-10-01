let presupuestos = [];

const budgetList = document.getElementById('presupuestosLista');
const budgetStatus = document.getElementById('presupuestoStatus');
const budgetForm = document.getElementById('presupuestoForm');
const budgetCategory = document.getElementById('presupuestoCategoria');
const budgetAmount = document.getElementById('presupuestoMonto');
const saveBudgetButton = budgetForm.querySelector('button[type="submit"]');

function renderBudgets() {
    budgetList.replaceChildren();
    if (!presupuestos.length) {
        const empty = document.createElement('p');
        empty.className = 'muted';
        empty.textContent = 'Todavía no agregaste límites. Puedes empezar por una categoría que quieras controlar.';
        budgetList.appendChild(empty);
        return;
    }

    presupuestos.forEach(budget => {
        const item = document.createElement('article');
        item.className = `budget-item ${budget.estado === 'cerca' ? 'near' : budget.estado === 'superado' ? 'exceeded' : ''}`;

        const head = document.createElement('div');
        head.className = 'budget-head';
        const category = document.createElement('span');
        category.textContent = budget.categoria;
        const limit = document.createElement('span');
        limit.textContent = money(budget.monto_maximo);
        head.append(category, limit);

        const progress = document.createElement('div');
        progress.className = 'budget-progress';
        progress.setAttribute('role', 'progressbar');
        progress.setAttribute('aria-label', `Presupuesto de ${budget.categoria}`);
        progress.setAttribute('aria-valuemin', '0');
        progress.setAttribute('aria-valuemax', '100');
        progress.setAttribute('aria-valuenow', String(Math.min(100, Math.round(budget.porcentaje))));
        const fill = document.createElement('span');
        fill.style.width = `${Math.min(100, Math.max(0, budget.porcentaje))}%`;
        progress.appendChild(fill);

        const detail = document.createElement('div');
        detail.className = 'budget-details';
        const spent = document.createElement('span');
        spent.textContent = `${money(budget.gastado)} gastados`;
        const percentage = document.createElement('span');
        percentage.textContent = `${Math.round(budget.porcentaje)}%`;
        detail.append(spent, percentage);

        const notice = document.createElement('p');
        notice.className = 'budget-note';
        notice.textContent = budget.estado === 'superado'
            ? 'Superaste este límite mensual.'
            : budget.estado === 'cerca'
                ? 'Ya usaste al menos el 80% del límite.'
                : 'Dentro del límite mensual.';

        const actions = document.createElement('div');
        actions.className = 'budget-actions';
        const edit = document.createElement('button');
        edit.type = 'button';
        edit.className = 'secondary';
        edit.textContent = 'Editar';
        edit.addEventListener('click', () => {
            budgetCategory.value = budget.categoria;
            budgetAmount.value = budget.monto_maximo;
            saveBudgetButton.textContent = 'Actualizar límite';
            budgetAmount.focus();
        });

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'budget-delete';
        remove.textContent = 'Quitar';
        remove.addEventListener('click', () => eliminarPresupuesto(budget.id));
        actions.append(edit, remove);
        item.append(head, progress, detail, notice, actions);
        budgetList.appendChild(item);
    });
}

async function cargarPresupuestos() {
    const response = await apiFetch('/api/presupuestos');
    if (!response.ok) throw new Error('No se pudieron cargar los presupuestos.');
    presupuestos = await response.json();
    renderBudgets();
}

async function guardarPresupuesto(event) {
    event.preventDefault();
    const category = budgetCategory.value;
    const amount = Number(budgetAmount.value);
    const existing = presupuestos.find(budget => budget.categoria === category);
    budgetStatus.className = 'status';
    budgetStatus.textContent = existing ? 'Actualizando límite…' : 'Guardando límite…';

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
        budgetForm.reset();
        saveBudgetButton.textContent = 'Guardar límite';
        budgetStatus.textContent = 'Presupuesto guardado.';
        budgetStatus.className = 'status success';
        await cargarPresupuestos();
    } catch (error) {
        budgetStatus.textContent = error.message;
        budgetStatus.className = 'status error';
    }
}

async function eliminarPresupuesto(id) {
    try {
        const response = await apiFetch(`/api/presupuestos/${id}`, { method: 'DELETE' });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'No se pudo quitar el presupuesto.');
        }
        budgetStatus.textContent = 'Presupuesto quitado.';
        budgetStatus.className = 'status success';
        await cargarPresupuestos();
    } catch (error) {
        budgetStatus.textContent = error.message;
        budgetStatus.className = 'status error';
    }
}

budgetCategory.addEventListener('change', () => {
    const existing = presupuestos.find(budget => budget.categoria === budgetCategory.value);
    saveBudgetButton.textContent = existing ? 'Actualizar límite' : 'Guardar límite';
});
budgetForm.addEventListener('submit', guardarPresupuesto);

async function iniciarPlanificacion() {
    const expensesResponse = await apiFetch('/gastos');
    if (!expensesResponse.ok) {
        throw new Error('No se pudieron cargar los gastos del mes.');
    }
    await cargarPresupuestos();
}

iniciarPlanificacion().catch(error => {
    budgetStatus.textContent = error.message;
    budgetStatus.className = 'status error';
});
