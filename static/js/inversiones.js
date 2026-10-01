let investments = [];
let chart;
let editingInvestment = null;

const endpoint = '/api/inversiones';
const elements = {
    form: document.getElementById('investmentForm'),
    formTitle: document.getElementById('formTitle'),
    editingId: document.getElementById('editingId'),
    activo: document.getElementById('activo'),
    cantidad: document.getElementById('cantidad'),
    currency: document.getElementById('monedaInversion'),
    amountLabel: document.getElementById('montoInvertidoLabel'),
    montoInvertido: document.getElementById('montoInvertido'),
    exchangeRateField: document.getElementById('tipoCambioField'),
    exchangeRate: document.getElementById('tipoCambioArsUsd'),
    currencyHint: document.getElementById('currencyHint'),
    rendimiento: document.getElementById('rendimiento'),
    saveButton: document.getElementById('saveButton'),
    cancelButton: document.getElementById('cancelButton'),
    refreshQuotes: document.getElementById('refreshQuotes'),
    status: document.getElementById('status'),
    quoteStatus: document.getElementById('quoteStatus'),
    total: document.getElementById('total'),
    invested: document.getElementById('invested'),
    currentProfit: document.getElementById('currentProfit'),
    currentProfitPercent: document.getElementById('currentProfitPercent'),
    resultMetric: document.getElementById('resultMetric'),
    profit: document.getElementById('profit'),
    assetCount: document.getElementById('assetCount'),
    chart: document.getElementById('portfolioChart'),
    chartEmpty: document.getElementById('chartEmpty'),
    portfolio: document.getElementById('portfolio')
};

const usd = value => new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2
}).format(Number(value) || 0);

function originalCurrencyAmount(value, currency) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2
    }).format(Number(value) || 0);
}

function numeric(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function currentValue(investment) {
    const quantity = numeric(investment.cantidad);
    const price = numeric(investment.precio_actual);
    return quantity > 0 && price > 0 ? quantity * price : numeric(investment.monto);
}

function setStatus(message, state = '') {
    elements.status.textContent = message;
    elements.status.className = state ? `status ${state}` : 'status';
}

function quoteDate(value) {
    if (!value) return 'Sin cotización actualizada';
    const timestamp = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`;
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return 'Fecha de cotización no disponible';
    return `Cotización actualizada: ${new Intl.DateTimeFormat('es-AR', {
        dateStyle: 'short',
        timeStyle: 'short'
    }).format(date)}`;
}

function formatPercent(value) {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function resetForm() {
    elements.form.reset();
    elements.currency.value = 'USD';
    updateCurrencyFields();
    elements.editingId.value = '';
    editingInvestment = null;
    elements.formTitle.textContent = 'Agregar inversión';
    elements.saveButton.textContent = 'Agregar inversión';
    elements.cancelButton.hidden = true;
    setStatus('');
}

function editInvestment(investment) {
    editingInvestment = investment;
    elements.editingId.value = investment.id;
    elements.activo.value = investment.activo || '';
    elements.cantidad.value = investment.cantidad || 1;
    elements.currency.value = investment.moneda_inversion || 'USD';
    elements.montoInvertido.value = numeric(investment.monto_invertido) > 0
        ? numeric(investment.monto_invertido_original) || numeric(investment.monto_invertido)
        : '';
    elements.exchangeRate.value = numeric(investment.tipo_cambio_ars_usd) > 0
        ? numeric(investment.tipo_cambio_ars_usd)
        : '';
    updateCurrencyFields();
    elements.rendimiento.value = investment.rendimiento || 0;
    elements.formTitle.textContent = 'Editar inversión';
    elements.saveButton.textContent = 'Guardar cambios';
    elements.cancelButton.hidden = false;
    elements.activo.focus();
}

function updateCurrencyFields() {
    const isArs = elements.currency.value === 'ARS';
    elements.amountLabel.textContent = `Total invertido (${elements.currency.value})`;
    elements.montoInvertido.placeholder = isArs ? 'Ej: 250000' : 'Ej: 250';
    elements.exchangeRateField.hidden = !isArs;
    elements.exchangeRate.disabled = !isArs;
    elements.exchangeRate.required = isArs;
    elements.currencyHint.hidden = !isArs;
}

function makeAssetRow(investment) {
    const quantity = numeric(investment.cantidad) || 1;
    const invested = numeric(investment.monto_invertido);
    const current = currentValue(investment);
    const gain = current - invested;
    const gainPercent = invested ? (gain / invested) * 100 : 0;
    const hasCostBasis = invested > 0;

    const row = document.createElement('article');
    row.className = 'investment-item';

    const description = document.createElement('div');
    description.className = 'investment-description';
    const name = document.createElement('strong');
    name.textContent = `${investment.activo}${investment.simbolo ? ` (${investment.simbolo})` : ''}`;
    const details = document.createElement('span');
    details.className = 'investment-meta';
    const originalAmount = numeric(investment.monto_invertido_original)
        || numeric(investment.monto_invertido);
    const originalCurrency = investment.moneda_inversion || 'USD';
    const originalCost = `Aporte ${originalCurrencyAmount(originalAmount, originalCurrency)}`
        + (originalCurrency === 'ARS'
            ? ` · TC ${numeric(investment.tipo_cambio_ars_usd).toLocaleString('es-AR')} ARS/USD`
            : '');
    details.textContent = hasCostBasis
        ? `${quantity.toLocaleString('es-AR')} unidades · ${originalCost} · Base ${usd(invested)} · Actual ${usd(current)}`
        : `${quantity.toLocaleString('es-AR')} unidades · Costo de compra sin registrar · Actual ${usd(current / quantity)} por unidad`;
    const updated = document.createElement('small');
    updated.className = 'investment-meta';
    updated.textContent = quoteDate(investment.cotizacion_actualizada);
    description.append(name, details, updated);

    const currentAmount = document.createElement('div');
    currentAmount.className = 'investment-current';
    const value = document.createElement('strong');
    value.textContent = usd(current);
    const result = document.createElement('span');
    result.className = hasCostBasis ? `investment-result ${gain >= 0 ? 'positive' : 'negative'}` : 'investment-result muted';
    result.textContent = hasCostBasis ? `${usd(gain)} (${formatPercent(gainPercent)})` : 'Registrá el precio original para ver el resultado';
    currentAmount.append(value, result);

    const actions = document.createElement('div');
    actions.className = 'investment-actions';
    const editButton = document.createElement('button');
    editButton.type = 'button';
    editButton.className = 'secondary';
    editButton.textContent = 'Editar';
    editButton.addEventListener('click', () => editInvestment(investment));
    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'delete';
    deleteButton.textContent = 'Eliminar';
    deleteButton.addEventListener('click', () => deleteInvestment(investment));
    actions.append(editButton, deleteButton);

    row.append(description, currentAmount, actions);
    return row;
}

function render() {
    const total = investments.reduce((sum, item) => sum + currentValue(item), 0);
    const knownCostInvestments = investments.filter(item => numeric(item.monto_invertido) > 0);
    const unknownCostCount = investments.length - knownCostInvestments.length;
    const invested = knownCostInvestments.reduce((sum, item) => sum + numeric(item.monto_invertido), 0);
    const knownCurrentValue = knownCostInvestments.reduce((sum, item) => sum + currentValue(item), 0);
    const gain = knownCurrentValue - invested;
    const gainPercent = invested ? (gain / invested) * 100 : 0;
    const projection = investments.reduce(
        (sum, item) => sum + currentValue(item) * numeric(item.rendimiento) / 100,
        0
    );

    elements.total.textContent = usd(total);
    elements.invested.textContent = usd(invested);
    elements.currentProfit.textContent = knownCostInvestments.length
        ? `${gain > 0 ? '+' : ''}${usd(gain)}`
        : '—';
    elements.currentProfitPercent.textContent = knownCostInvestments.length
        ? unknownCostCount
            ? `Resultado parcial · ${unknownCostCount} ${unknownCostCount === 1 ? 'activo sin costo' : 'activos sin costo'}`
            : `${formatPercent(gainPercent)} sobre el capital`
        : 'Registrá precios de compra para ver el resultado';
    elements.resultMetric.classList.toggle('positive', knownCostInvestments.length > 0 && gain >= 0);
    elements.resultMetric.classList.toggle('negative', knownCostInvestments.length > 0 && gain < 0);
    elements.profit.textContent = usd(projection);
    elements.assetCount.textContent = `${investments.length} ${investments.length === 1 ? 'activo' : 'activos'}`;

    elements.portfolio.replaceChildren();
    if (investments.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-state';
        empty.textContent = 'Todavía no agregaste activos a tu cartera.';
        elements.portfolio.appendChild(empty);
    } else {
        investments.forEach(item => elements.portfolio.appendChild(makeAssetRow(item)));
    }

    if (chart) chart.destroy();
    elements.chart.hidden = investments.length === 0;
    elements.chartEmpty.hidden = investments.length !== 0;
    if (investments.length > 0) {
        chart = new Chart(elements.chart, {
            type: 'doughnut',
            data: {
                labels: investments.map(item => item.activo),
                datasets: [{
                    data: investments.map(currentValue),
                    backgroundColor: ['#4f46e5', '#16805b', '#d97706', '#c2414d', '#0891b2', '#8b5cf6', '#38bdf8']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
}

async function load() {
    const response = await apiFetch(endpoint);
    if (!response.ok) throw new Error('No se pudo cargar la cartera.');
    investments = await response.json();
    render();
}

async function responseError(response, fallback) {
    try {
        const body = await response.json();
        return body.detail || fallback;
    } catch {
        return fallback;
    }
}

async function deleteInvestment(investment) {
    if (!window.confirm(`¿Eliminar ${investment.activo} de la cartera?`)) return;
    try {
        const response = await apiFetch(`${endpoint}/${investment.id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await responseError(response, 'No se pudo eliminar la inversión.'));
        if (elements.editingId.value === String(investment.id)) resetForm();
        await load();
        setStatus('Inversión eliminada.', 'success');
    } catch (error) {
        setStatus(error.message || 'No se pudo eliminar la inversión.', 'error');
    }
}

elements.form.addEventListener('submit', async event => {
    event.preventDefault();
    const id = elements.editingId.value;
    const quantity = Number(elements.cantidad.value);
    const currency = elements.currency.value;
    const originalAmount = Number(elements.montoInvertido.value);
    const exchangeRate = currency === 'ARS' ? Number(elements.exchangeRate.value) : 1;
    const invested = currency === 'ARS' ? originalAmount / exchangeRate : originalAmount;
    const assetName = elements.activo.value.trim();
    const sameAsset = editingInvestment
        && editingInvestment.activo.trim().toLocaleLowerCase() === assetName.toLocaleLowerCase();
    const symbol = sameAsset ? editingInvestment.simbolo : null;
    const hasMarketQuote = sameAsset && editingInvestment.cotizacion_actualizada;
    const currentPrice = hasMarketQuote && numeric(editingInvestment.precio_actual) > 0
        ? numeric(editingInvestment.precio_actual)
        : invested / quantity;
    const payload = {
        activo: assetName,
        simbolo: symbol,
        cantidad: quantity,
        precio_actual: currentPrice,
        monto: quantity * currentPrice,
        monto_invertido: invested,
        monto_invertido_original: originalAmount,
        moneda_inversion: currency,
        tipo_cambio_ars_usd: exchangeRate,
        rendimiento: Number(elements.rendimiento.value || 0)
    };

    elements.saveButton.disabled = true;
    setStatus(id ? 'Guardando los cambios...' : 'Identificando el activo y consultando su cotización...');
    try {
        const response = await apiFetch(id ? `${endpoint}/${id}` : endpoint, {
            method: id ? 'PUT' : 'POST',
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error(await responseError(response, 'No se pudo guardar la inversión.'));
        const savedInvestment = await response.json();
        resetForm();
        await load();
        if (id) {
            setStatus('Inversión actualizada.', 'success');
        } else if (savedInvestment.simbolo && savedInvestment.cotizacion_actualizada) {
            setStatus('Inversión guardada y cotización actualizada.', 'success');
        } else if (savedInvestment.simbolo) {
            setStatus('Inversión guardada. Identificamos el activo; su cotización no está disponible ahora.', 'notice');
        } else {
            setStatus('Inversión guardada. No encontramos una cotización; su valor parte del total invertido.', 'notice');
        }
    } catch (error) {
        setStatus(error.message || 'No se pudo guardar la inversión.', 'error');
    } finally {
        elements.saveButton.disabled = false;
    }
});

elements.currency.addEventListener('change', updateCurrencyFields);
elements.cancelButton.addEventListener('click', resetForm);

elements.refreshQuotes.addEventListener('click', async () => {
    elements.refreshQuotes.disabled = true;
    elements.quoteStatus.textContent = 'Consultando cotizaciones...';
    elements.quoteStatus.className = 'quote-status muted';
    try {
        const response = await apiFetch(`${endpoint}/actualizar-cotizaciones`, { method: 'POST' });
        if (!response.ok) throw new Error(await responseError(response, 'No se pudieron actualizar las cotizaciones.'));
        const result = await response.json();
        const updated = result.resultados.filter(item => item.actualizada);
        const unavailable = result.resultados.filter(item => !item.actualizada);
        await load();

        const message = [`${updated.length} ${updated.length === 1 ? 'cotización actualizada' : 'cotizaciones actualizadas'}.`];
        if (unavailable.length) {
            message.push(`Sin actualizar: ${unavailable.map(item => `${item.simbolo || `activo ${item.id}`} (${item.motivo})`).join(', ')}.`);
        }
        elements.quoteStatus.textContent = message.join(' ');
        elements.quoteStatus.className = `quote-status ${unavailable.length ? 'notice' : 'success'}`;
    } catch (error) {
        elements.quoteStatus.textContent = error.message || 'No se pudieron actualizar las cotizaciones.';
        elements.quoteStatus.className = 'quote-status error';
    } finally {
        elements.refreshQuotes.disabled = false;
    }
});

load().catch(error => {
    elements.quoteStatus.textContent = error.message || 'No se pudo cargar la cartera.';
    elements.quoteStatus.className = 'quote-status error';
    elements.portfolio.textContent = error.message || 'No se pudo cargar la cartera.';
});
