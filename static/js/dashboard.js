let categoryChart;
let trendChart;
let gastos = [];

const totalEl = document.getElementById('totalMes');
const countEl = document.getElementById('cantidadGastos');
const majorEl = document.getElementById('categoriaMayor');
const filter = document.getElementById('filtroCategoria');
const list = document.getElementById('tablaGastos');
const categoryChartEl = document.getElementById('categoryChart');
const trendChartEl = document.getElementById('trendChart');
const monthFilter = document.getElementById('filtroMes');

function currentMonthKey() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function monthKey(expense) {
    return expense.fecha.slice(0, 7);
}

function resumenPorCategoria(expenses) {
    const totals = new Map();
    for (const expense of expenses) {
        const category = expense.categoria || 'General';
        const summary = totals.get(category) || { categoria: category, total: 0, cantidad: 0 };
        summary.total += Number(expense.monto);
        summary.cantidad += 1;
        totals.set(category, summary);
    }
    return [...totals.values()];
}

function renderCategory(data) {
    if (categoryChart) categoryChart.destroy();
    categoryChart = new Chart(categoryChartEl, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.categoria),
            datasets: [{
                data: data.map(item => Number(item.total)),
                backgroundColor: ['#4f46e5', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#38bdf8']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
}

function renderTrend(data, throughMonth) {
    const [selectedYear, selectedMonth] = throughMonth.split('-').map(Number);
    const months = Array.from({ length: 6 }, (_, index) => {
        const date = new Date(selectedYear, selectedMonth - 1 - (5 - index), 1);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    });
    const totalsByMonth = new Map(months.map(month => [month, 0]));
    data.forEach(expense => {
        const key = monthKey(expense);
        if (totalsByMonth.has(key)) {
            totalsByMonth.set(key, totalsByMonth.get(key) + Number(expense.monto));
        }
    });
    const labels = months.map(month => {
        const [year, monthNumber] = month.split('-').map(Number);
        return new Intl.DateTimeFormat('es-AR', { month: 'short', year: 'numeric' })
            .format(new Date(year, monthNumber - 1, 1));
    });
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(trendChartEl, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Total gastado',
                data: months.map(month => totalsByMonth.get(month)),
                backgroundColor: '#4f46e5'
            }]
        },
        options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });
}

function renderList(expenses) {
    const selected = filter.value;
    const visibleExpenses = selected === 'Todas'
        ? expenses
        : expenses.filter(expense => (expense.categoria || 'General') === selected);
    list.replaceChildren();

    if (!visibleExpenses.length) {
        const empty = document.createElement('div');
        empty.className = 'record';
        empty.textContent = 'No hay gastos para este filtro.';
        list.appendChild(empty);
        return;
    }

    visibleExpenses.forEach(expense => {
        const row = document.createElement('div');
        row.className = 'expense-item';
        const details = document.createElement('span');
        const description = document.createElement('strong');
        description.textContent = expense.descripcion;
        const metadata = document.createElement('small');
        metadata.textContent = `${expense.categoria || 'General'} · ${new Date(expense.fecha).toLocaleDateString('es-AR')}`;
        details.append(description, document.createElement('br'), metadata);

        const amount = document.createElement('strong');
        amount.textContent = money(expense.monto);
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = 'Eliminar';
        remove.addEventListener('click', () => eliminarGasto(expense.id));
        row.append(details, amount, remove);
        list.appendChild(row);
    });
}

function renderSelectedMonth() {
    const selectedMonth = monthFilter.value;
    const expenses = gastos.filter(expense => monthKey(expense) === selectedMonth);
    const summary = resumenPorCategoria(expenses);
    totalEl.textContent = money(summary.reduce((sum, item) => sum + Number(item.total), 0));
    countEl.textContent = expenses.length;
    majorEl.textContent = summary.length
        ? summary.reduce((largest, item) => Number(largest.total) > Number(item.total) ? largest : item).categoria
        : '-';

    const selectedCategory = filter.value;
    filter.replaceChildren(new Option('Todas las categorías', 'Todas'));
    [...new Set(expenses.map(expense => expense.categoria || 'General'))]
        .sort((a, b) => a.localeCompare(b, 'es'))
        .forEach(category => filter.add(new Option(category, category)));
    filter.value = expenses.some(expense => (expense.categoria || 'General') === selectedCategory)
        ? selectedCategory
        : 'Todas';

    renderCategory(summary);
    renderTrend(gastos, selectedMonth);
    renderList(expenses);
}

async function load() {
    const expensesResponse = await apiFetch('/gastos');
    if (!expensesResponse.ok) {
        throw new Error('No se pudieron cargar los gastos.');
    }
    gastos = await expensesResponse.json();
    renderSelectedMonth();
}

async function eliminarGasto(id) {
    try {
        const response = await apiFetch(`/gastos/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('No se pudo eliminar el gasto.');
        await load();
    } catch (error) {
        document.getElementById('manualStatus').textContent = error.message;
        document.getElementById('manualStatus').className = 'status error';
    }
}

filter.addEventListener('change', renderSelectedMonth);
monthFilter.value = currentMonthKey();
monthFilter.addEventListener('change', renderSelectedMonth);

document.getElementById('gastoForm').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const status = document.getElementById('manualStatus');
    const payload = {
        monto: Number(document.getElementById('monto').value),
        descripcion: document.getElementById('descripcion').value.trim(),
        categoria: document.getElementById('categoria').value
    };
    try {
        const response = await apiFetch('/gastos', { method: 'POST', body: JSON.stringify(payload) });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'No se pudo guardar el gasto.');
        }
        status.textContent = 'Gasto guardado.';
        status.className = 'status success';
        form.reset();
        await load();
    } catch (error) {
        status.textContent = error.message;
        status.className = 'status error';
    }
});

document.getElementById('iaForm').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const status = document.getElementById('iaStatus');
    status.className = 'status';
    status.textContent = 'Procesando con IA…';
    try {
        const response = await apiFetch('/chat/procesar', {
            method: 'POST',
            body: JSON.stringify({ mensaje: document.getElementById('mensaje').value.trim() })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'No se pudo procesar el mensaje.');
        }
        const result = await response.json();
        if (!result.es_gasto) {
            status.textContent = result.respuesta_chat;
            status.className = 'status notice';
            return;
        }
        status.textContent = `Gasto registrado: ${result.gasto.descripcion} (${money(result.gasto.monto)})`;
        status.className = 'status success';
        form.reset();
        await load();
    } catch (error) {
        status.textContent = error.message;
        status.className = 'status error';
    }
});

load().catch(error => {
    totalEl.textContent = 'Error';
    majorEl.textContent = '-';
    list.textContent = error.message;
});
