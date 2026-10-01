function recurringPanel(kind) {
    const isExpense = kind === 'expense';
    const endpoint = isExpense ? '/gastos/fijos' : '/api/ingresos/fijos';
    const label = isExpense ? 'gasto' : 'ingreso';
    const host = isExpense ? document.getElementById('gastosFijosPanel') : null;
    const mount = host || document.createElement('section');
    if (!host) mount.className = 'recurring-panel';
    mount.replaceChildren();

    const heading = document.createElement('div');
    heading.className = 'section-head';
    const headingContent = document.createElement('div');
    const title = document.createElement('h2');
    title.textContent = isExpense ? 'Gastos fijos mensuales' : 'Ingresos fijos mensuales';
    const description = document.createElement('p');
    description.className = 'muted';
    description.textContent = `Se registran automáticamente una vez por mes. Puedes editarlos o quitarlos cuando quieras.`;
    headingContent.append(title, description);

    const toggle = document.createElement('button');
    toggle.className = 'secondary';
    toggle.type = 'button';
    toggle.textContent = `Agregar ${label} fijo`;
    heading.append(headingContent, toggle);

    const form = document.createElement('form');
    form.hidden = true;
    const idInput = document.createElement('input');
    idInput.type = 'hidden';
    const descriptionInput = document.createElement('input');
    descriptionInput.required = true;
    descriptionInput.maxLength = 120;
    descriptionInput.placeholder = isExpense ? 'Descripción' : 'Motivo';
    descriptionInput.setAttribute('aria-label', isExpense ? 'Descripción del gasto fijo' : 'Motivo del ingreso fijo');
    const categorySelect = document.createElement('select');
    categorySelect.setAttribute('aria-label', 'Categoría del gasto fijo');
    if (isExpense) {
        for (const category of [
            'Alimentación',
            'Transporte',
            'Servicios',
            'Entretenimiento',
            'Salud',
            'Compras',
            'General'
        ]) {
            categorySelect.add(new Option(category, category));
        }
    }
    const amountInput = document.createElement('input');
    amountInput.type = 'number';
    amountInput.min = '0.01';
    amountInput.step = '0.01';
    amountInput.placeholder = 'Monto mensual';
    amountInput.setAttribute('aria-label', `Monto mensual del ${label} fijo`);
    amountInput.required = true;
    const dayLabel = document.createElement('label');
    dayLabel.textContent = 'Día del mes de registro automático';
    const dayInput = document.createElement('input');
    dayInput.type = 'number';
    dayInput.min = '1';
    dayInput.max = '31';
    dayInput.value = '1';
    dayInput.required = true;
    dayLabel.appendChild(dayInput);
    const dayHelp = document.createElement('small');
    dayHelp.className = 'muted';
    dayHelp.textContent = 'Si el mes es más corto, se usa su último día.';
    const save = document.createElement('button');
    save.type = 'submit';
    save.textContent = `Guardar ${label} fijo`;
    form.append(idInput, descriptionInput);
    if (isExpense) form.appendChild(categorySelect);
    form.append(amountInput, dayLabel, dayHelp, save);

    const status = document.createElement('p');
    status.className = 'status';
    status.setAttribute('aria-live', 'polite');
    const list = document.createElement('div');
    list.className = 'records';
    const panel = document.createElement('div');
    panel.className = 'card recurring-card';
    panel.append(heading, form, status, list);
    mount.appendChild(panel);
    if (!host) document.querySelector('.container').appendChild(mount);

    toggle.addEventListener('click', () => {
        form.hidden = !form.hidden;
        toggle.textContent = form.hidden ? `Agregar ${label} fijo` : 'Cancelar';
        if (!form.hidden) descriptionInput.focus();
    });

    function setStatus(message, kind = '') {
        status.textContent = message;
        status.className = `status ${kind}`.trim();
    }

    function resetForm() {
        form.reset();
        idInput.value = '';
        dayInput.value = '1';
        save.textContent = `Guardar ${label} fijo`;
    }

    function editItem(item) {
        idInput.value = item.id;
        descriptionInput.value = isExpense ? item.descripcion : item.motivo;
        amountInput.value = item.monto;
        dayInput.value = item.dia_mes;
        if (isExpense) categorySelect.value = item.categoria;
        save.textContent = `Actualizar ${label} fijo`;
        form.hidden = false;
        toggle.textContent = 'Cancelar';
        descriptionInput.focus();
    }

    async function load() {
        const response = await apiFetch(endpoint);
        if (!response.ok) throw new Error(`No se pudieron cargar los ${label}s fijos.`);
        const items = await response.json();
        list.replaceChildren();
        if (!items.length) {
            const empty = document.createElement('p');
            empty.className = 'muted';
            empty.textContent = `Todavía no agregaste ${label}s fijos.`;
            list.appendChild(empty);
            return;
        }

        items.forEach(item => {
            const row = document.createElement('article');
            row.className = 'record';
            const details = document.createElement('span');
            const itemTitle = document.createElement('strong');
            itemTitle.textContent = isExpense ? item.descripcion : item.motivo;
            const metadata = document.createElement('small');
            metadata.className = 'muted';
            metadata.textContent = `${money(item.monto)} · Día ${item.dia_mes} · ${item.activo ? 'Activo' : 'Pausado'}`;
            details.append(itemTitle, document.createElement('br'), metadata);

            const actions = document.createElement('div');
            actions.className = 'recurring-actions';
            const edit = document.createElement('button');
            edit.type = 'button';
            edit.className = 'secondary';
            edit.textContent = 'Editar';
            edit.addEventListener('click', () => editItem(item));
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'budget-delete';
            remove.textContent = 'Eliminar';
            remove.addEventListener('click', () => deleteItem(item.id));
            actions.append(edit, remove);
            row.append(details, actions);
            list.appendChild(row);
        });
    }

    async function deleteItem(itemId) {
        try {
            const response = await apiFetch(`${endpoint}/${itemId}`, { method: 'DELETE' });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `No se pudo eliminar el ${label} fijo.`);
            }
            setStatus(`${isExpense ? 'Gasto' : 'Ingreso'} fijo eliminado.`, 'success');
            await load();
        } catch (error) {
            setStatus(error.message, 'error');
        }
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const itemId = idInput.value;
        const payload = {
            monto: Number(amountInput.value),
            dia_mes: Number(dayInput.value),
            activo: true
        };
        payload[isExpense ? 'descripcion' : 'motivo'] = descriptionInput.value.trim();
        if (isExpense) payload.categoria = categorySelect.value;

        try {
            const response = await apiFetch(
                itemId ? `${endpoint}/${itemId}` : endpoint,
                {
                    method: itemId ? 'PUT' : 'POST',
                    body: JSON.stringify(payload)
                }
            );
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `No se pudo guardar el ${label} fijo.`);
            }
            setStatus(`${isExpense ? 'Gasto' : 'Ingreso'} fijo guardado.`, 'success');
            resetForm();
            form.hidden = true;
            toggle.textContent = `Agregar ${label} fijo`;
            await load();
        } catch (error) {
            setStatus(error.message, 'error');
        }
    });

    load().catch(error => setStatus(error.message, 'error'));
}

if (location.pathname === '/planificacion') recurringPanel('expense');
if (location.pathname === '/ingresos') recurringPanel('income');
