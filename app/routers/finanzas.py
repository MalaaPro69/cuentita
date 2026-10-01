from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
from app.database.connection import get_db
from app.models.db_models import Usuario
from app.schemas.pydantic_schemas import (
    IngresoCreate,
    IngresoFijoCreate,
    IngresoFijoResponse,
    IngresoResponse,
    InversionCreate,
    InversionResponse,
    PresupuestoCreate,
    PresupuestoResumen,
    PresupuestoResponse,
)
from app.services.auth_service import get_current_user
from app.controllers import finanzas_controller, presupuesto_controller

router = APIRouter(tags=["Ingresos e Inversiones"])
FRONTEND_DIR = Path(__file__).resolve().parents[2]


@router.get("/api/presupuestos", response_model=List[PresupuestoResumen])
def listar_presupuestos(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    return presupuesto_controller.listar_presupuestos(db, usuario.id)


@router.post(
    "/api/presupuestos",
    response_model=PresupuestoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_presupuesto(
    presupuesto: PresupuestoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    registro = presupuesto_controller.crear_presupuesto(
        db,
        presupuesto.categoria,
        presupuesto.monto_maximo,
        usuario.id,
    )
    if not registro:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un presupuesto para esa categoría")
    return registro


@router.put("/api/presupuestos/{presupuesto_id}", response_model=PresupuestoResponse)
def actualizar_presupuesto(
    presupuesto_id: int,
    presupuesto: PresupuestoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    try:
        registro = presupuesto_controller.actualizar_presupuesto(
            db,
            presupuesto_id,
            presupuesto.categoria,
            presupuesto.monto_maximo,
            usuario.id,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un presupuesto para esa categoría") from exc
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presupuesto no encontrado")
    return registro


@router.delete("/api/presupuestos/{presupuesto_id}")
def eliminar_presupuesto(
    presupuesto_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    if not presupuesto_controller.eliminar_presupuesto(db, presupuesto_id, usuario.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Presupuesto no encontrado")
    return {"ok": True}


@router.post("/api/ingresos", response_model=IngresoResponse)
def crear_ingreso(ingreso: IngresoCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    return finanzas_controller.crear_ingreso(db, ingreso, usuario.id)


@router.get("/api/ingresos", response_model=List[IngresoResponse])
def listar_ingresos(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    finanzas_controller.generar_ingresos_fijos_del_mes(db, usuario.id)
    return finanzas_controller.listar_ingresos(db, usuario.id)


@router.post("/api/ingresos/fijos", response_model=IngresoFijoResponse)
def crear_ingreso_fijo(ingreso: IngresoFijoCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    return finanzas_controller.crear_ingreso_fijo(db, ingreso, usuario.id)


@router.get("/api/ingresos/fijos", response_model=List[IngresoFijoResponse])
def listar_ingresos_fijos(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    return finanzas_controller.listar_ingresos_fijos(db, usuario.id)


@router.put("/api/ingresos/fijos/{fijo_id}", response_model=IngresoFijoResponse)
def editar_ingreso_fijo(fijo_id: int, ingreso: IngresoFijoCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    registro = finanzas_controller.actualizar_ingreso_fijo(db, fijo_id, ingreso, usuario.id)
    if not registro:
        raise HTTPException(status_code=404, detail="Ingreso fijo no encontrado")
    return registro


@router.delete("/api/ingresos/fijos/{fijo_id}")
def eliminar_ingreso_fijo(fijo_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    if not finanzas_controller.eliminar_ingreso_fijo(db, fijo_id, usuario.id):
        raise HTTPException(status_code=404, detail="Ingreso fijo no encontrado")
    return {"ok": True}


@router.delete("/api/ingresos/{ingreso_id}")
def borrar_ingreso(ingreso_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    if not finanzas_controller.eliminar_ingreso(db, ingreso_id, usuario.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso no encontrado")
    return {"ok": True}


@router.post("/api/inversiones", response_model=InversionResponse)
def crear_inversion(
    inversion: InversionCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> InversionResponse:
    registro = finanzas_controller.crear_inversion(db, inversion, int(usuario.id))
    return InversionResponse.model_validate(registro)


@router.get("/api/inversiones", response_model=List[InversionResponse])
def listar_inversiones(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    return finanzas_controller.listar_inversiones(db, usuario.id)


@router.post("/api/inversiones/actualizar-cotizaciones")
def actualizar_cotizaciones(db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    return {"resultados": finanzas_controller.actualizar_cotizaciones(db, usuario.id)}


@router.put("/api/inversiones/{inversion_id}", response_model=InversionResponse)
def actualizar_inversion(inversion_id: int, inversion: InversionCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    registro = finanzas_controller.actualizar_inversion(db, inversion_id, inversion, usuario.id)
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inversión no encontrada")
    return registro


@router.delete("/api/inversiones/{inversion_id}")
def borrar_inversion(inversion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    if not finanzas_controller.eliminar_inversion(db, inversion_id, usuario.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inversión no encontrada")
    return {"ok": True}


INVESTMENT_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cuentita | Inversiones</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root { --ink:#172033; --muted:#667085; --line:#dfe5ef; --panel:#fff; --accent:#4f46e5; --dark:#3730a3; --green:#16805b; --red:#c2414d; }
* { box-sizing:border-box; } body { margin:0; color:var(--ink); font-family:Arial,sans-serif; background:linear-gradient(135deg,#eef2ff,#fbfcff); }
.container { width:min(1100px,92vw); margin:auto; padding:28px 0 60px; } .topbar { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:26px; }
.brand { color:var(--accent); font-weight:800; font-size:2rem; } .nav { display:flex; gap:8px; flex-wrap:wrap; } .nav a,.logout { border:1px solid var(--line); background:var(--panel); border-radius:10px; padding:10px 13px; color:var(--ink); text-decoration:none; cursor:pointer; font-weight:700; }
.nav a.active,.logout { background:var(--accent); color:white; border-color:var(--accent); } .intro { color:var(--muted); margin:0 0 22px; } .card { background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px; box-shadow:0 12px 26px #4f46e512; margin-bottom:20px; }
.layout { display:grid; grid-template-columns:minmax(280px,360px) 1fr; gap:20px; } form { display:grid; gap:12px; } label { font-weight:700; font-size:.9rem; } input,button { font:inherit; } input { width:100%; padding:12px; border:1px solid var(--line); border-radius:10px; margin-top:6px; } button { border:0; border-radius:10px; padding:12px 15px; color:white; background:linear-gradient(135deg,var(--accent),var(--dark)); font-weight:700; cursor:pointer; } .status { min-height:22px; margin-top:10px; color:var(--green); }
.metric-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px; } .metric { background:#f7f9fc; border:1px solid var(--line); border-radius:12px; padding:14px; } .metric small { color:var(--muted); display:block; margin-bottom:6px; } .metric strong { font-size:1.25rem; } .chart-wrap { height:310px; position:relative; } .portfolio { display:grid; gap:10px; margin-top:20px; }
.asset { display:grid; grid-template-columns:1fr auto auto; align-items:center; gap:12px; border:1px solid var(--line); border-radius:12px; padding:13px; } .asset small { display:block; color:var(--muted); margin-top:4px; } .asset-value { font-weight:800; text-align:right; } .asset-actions { display:flex; gap:6px; } .secondary { background:#eef2ff; color:var(--dark); padding:8px 10px; } .delete { background:#fff1f2; color:var(--red); padding:8px 10px; }
.editing { background:#fffdf4; border-color:#f2cf75; } .dollar-note { color:var(--muted); font-size:.85rem; margin-top:4px; } @media(max-width:760px) { .topbar,.asset { align-items:stretch; flex-direction:column; } .layout { grid-template-columns:1fr; } .metric-grid { grid-template-columns:1fr; } .asset-value { text-align:left; } .nav a,.logout { text-align:center; } }
</style></head><body><main class="container">
<header class="topbar"><div class="brand">Cuentita</div><nav class="nav"><a href="/menu">Menú</a><a href="/dashboard">Gastos</a><a href="/ingresos">Ingresos</a><a class="active" href="/inversiones">Inversiones</a><button class="logout" onclick="logout()">Salir</button></nav></header>
<section class="card"><h1>Mi cartera</h1><p class="intro">Registrá cantidades y precios en dólares. El valor de cada posición se calcula como cantidad por precio actual.</p><div class="layout"><section><form id="investmentForm"><input type="hidden" id="editingId"><label>Activo<input id="activo" placeholder="Ej: Bitcoin, CEDEAR de Apple" required></label><label>Símbolo de mercado<input id="simbolo" placeholder="Ej: BTC, ETH, AAPL" maxlength="40"><div class="dollar-note">Usá un símbolo para habilitar cotizaciones automáticas.</div><label>Cantidad<input id="cantidad" type="number" min="0.00000001" step="any" placeholder="Ej: 2" required></label><label>Precio actual por unidad (USD)<input id="precioActual" type="number" min="0" step="0.01" placeholder="Ej: 150.00" required></label><label>Rendimiento estimado (%)<input id="rendimiento" type="number" step="0.01" placeholder="Ej: 8.5"></label><div class="dollar-note">Todos los valores de esta pestaña están expresados en USD.</div><button id="saveButton" type="submit">Agregar inversión</button><button id="cancelButton" type="button" class="secondary" hidden>Cancelar edición</button></form><div id="status" class="status"></div></section><section><div class="metric-grid"><div class="metric"><small>Valor total</small><strong id="total">US$ 0</strong></div><div class="metric"><small>Activos</small><strong id="count">0</strong></div><div class="metric"><small>Ganancia/pérdida estimada</small><strong id="profit">US$ 0</strong></div></div><button id="refreshQuotes" type="button">Actualizar cotizaciones</button><div class="dollar-note">Criptos: CoinGecko. Acciones/CEDEARs compatibles: Yahoo Finance.</div><div class="chart-wrap"><canvas id="portfolioChart"></canvas></div></section></div></section>
<section class="card"><h2>Activos de la cartera</h2><div id="portfolio" class="portfolio"></div></section>
</main><script>
const endpoint='/api/inversiones';let data=[];let chart;
const money=value=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(Number(value||0));
const csrfToken=()=>{const cookie=document.cookie.split('; ').find(item=>item.startsWith('csrf_token='));return cookie?decodeURIComponent(cookie.slice('csrf_token='.length)):'';};
const api=(url,options={})=>fetch(url,{...options,credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json','X-CSRF-Token':csrfToken(),...(options.headers||{})}});
async function logout(){await fetch('/logout',{method:'POST',headers:{'X-CSRF-Token':csrfToken()}});location.href='/login';}
function valueOf(item){const calculated=Number(item.cantidad||0)*Number(item.precio_actual||0);return calculated>0?calculated:Number(item.monto||0);}
function resetForm(){document.getElementById('investmentForm').reset();document.getElementById('editingId').value='';document.getElementById('saveButton').textContent='Agregar inversión';document.getElementById('cancelButton').hidden=true;}
function editItem(item){document.getElementById('editingId').value=item.id;document.getElementById('activo').value=item.activo;document.getElementById('simbolo').value=item.simbolo||'';document.getElementById('cantidad').value=item.cantidad||1;document.getElementById('precioActual').value=item.precio_actual||item.monto||0;document.getElementById('rendimiento').value=item.rendimiento||0;document.getElementById('saveButton').textContent='Actualizar inversión';document.getElementById('cancelButton').hidden=false;document.getElementById('investmentForm').scrollIntoView({behavior:'smooth'});}
function render(){const total=data.reduce((sum,item)=>sum+valueOf(item),0);const profit=data.reduce((sum,item)=>sum+valueOf(item)*Number(item.rendimiento||0)/100,0);document.getElementById('total').textContent=money(total);document.getElementById('count').textContent=data.length;document.getElementById('profit').textContent=money(profit);if(chart)chart.destroy();chart=new Chart(document.getElementById('portfolioChart'),{type:'doughnut',data:{labels:data.map(item=>item.activo),datasets:[{data:data.map(valueOf),backgroundColor:['#4f46e5','#16805b','#d97706','#c2414d','#0891b2','#7c3aed','#65a30d'],borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom'},tooltip:{callbacks:{label:context=>`${context.label}: ${money(context.raw)} (${total?((context.raw/total)*100).toFixed(1):0}%)`}}}}});const list=document.getElementById('portfolio');list.innerHTML='';if(!data.length){list.innerHTML='<div class="asset">Todavía no hay inversiones registradas.</div>';return;}data.forEach(item=>{const row=document.createElement('div');row.className='asset';const info=document.createElement('div');const variation=item.variacion_24h==null?'Sin cotización automática':`${Number(item.variacion_24h).toFixed(2)}% en 24 h`;info.innerHTML=`<strong>${item.activo}${item.simbolo?` (${item.simbolo})`:''}</strong><small>${item.cantidad||1} unidades · US$ ${Number(item.precio_actual||0).toFixed(2)} por unidad · ${total?((valueOf(item)/total)*100).toFixed(1):0}% de cartera · ${variation}</small>`;const amount=document.createElement('div');amount.className='asset-value';amount.textContent=money(valueOf(item));const actions=document.createElement('div');actions.className='asset-actions';const edit=document.createElement('button');edit.className='secondary';edit.textContent='Editar';edit.onclick=()=>editItem(item);const del=document.createElement('button');del.className='delete';del.textContent='Eliminar';del.onclick=async()=>{await api(`${endpoint}/${item.id}`,{method:'DELETE'});load();};actions.append(edit,del);row.append(info,amount,actions);list.appendChild(row);});}
async function load(){const res=await api(endpoint);if(!res.ok){location.href='/login';return;}data=await res.json();render();}
document.getElementById('cancelButton').addEventListener('click',resetForm);document.getElementById('refreshQuotes').addEventListener('click',async()=>{const status=document.getElementById('status');status.textContent='Consultando cotizaciones...';const res=await api('/api/inversiones/actualizar-cotizaciones',{method:'POST'});const result=await res.json();const updated=result.resultados.filter(item=>item.actualizada).length;status.textContent=`${updated} cotización(es) actualizada(s).`;load();});document.getElementById('investmentForm').addEventListener('submit',async event=>{event.preventDefault();const id=document.getElementById('editingId').value;const cantidad=Number(document.getElementById('cantidad').value);const precio=Number(document.getElementById('precioActual').value);const payload={activo:document.getElementById('activo').value.trim(),simbolo:document.getElementById('simbolo').value.trim().toUpperCase()||null,cantidad,precio_actual:precio,monto:cantidad*precio,rendimiento:Number(document.getElementById('rendimiento').value||0)};const res=await api(id?`${endpoint}/${id}`:endpoint,{method:id?'PUT':'POST',body:JSON.stringify(payload)});const status=document.getElementById('status');if(!res.ok){const error=await res.json();status.textContent=error.detail||'No se pudo guardar';status.style.color='var(--red)';return;}status.textContent=id?'Inversión actualizada.':'Inversión agregada.';status.style.color='var(--green)';resetForm();load();});load();
</script></body></html>
"""


SHELL = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cuentita | {title}</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {{ --ink:#172033; --muted:#667085; --line:#dfe5ef; --panel:#fff; --accent:#4f46e5; --accent-dark:#3730a3; --green:#16805b; --red:#c2414d; }}
* {{ box-sizing:border-box; }} body {{ margin:0; color:var(--ink); font-family:Arial,sans-serif; background:linear-gradient(135deg,#eef2ff,#fbfcff); }}
.container {{ width:min(1100px,92vw); margin:auto; padding:28px 0 60px; }} .topbar {{ display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:26px; }}
.brand {{ color:var(--accent); font-weight:800; font-size:2rem; }} .nav {{ display:flex; gap:8px; flex-wrap:wrap; }} .nav a,.logout {{ border:1px solid var(--line); background:var(--panel); border-radius:10px; padding:10px 13px; color:var(--ink); text-decoration:none; cursor:pointer; font-weight:700; }}
.nav a.active,.logout {{ background:var(--accent); color:white; border-color:var(--accent); }} .layout {{ display:grid; grid-template-columns:minmax(280px,360px) 1fr; gap:20px; }} .card {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:22px; box-shadow:0 12px 26px #4f46e512; }}
 h1 {{ margin:0 0 8px; }} .intro {{ color:var(--muted); margin:0 0 20px; }} form {{ display:grid; gap:12px; }} label {{ font-weight:700; font-size:.9rem; }} input,button {{ font:inherit; }} input {{ width:100%; padding:12px; border:1px solid var(--line); border-radius:10px; margin-top:6px; }} button {{ border:0; border-radius:10px; padding:12px 15px; color:white; background:linear-gradient(135deg,var(--accent),var(--accent-dark)); font-weight:700; cursor:pointer; }} .status {{ min-height:22px; margin-top:10px; color:var(--green); }} .chart-wrap {{ min-height:300px; }} .metric-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-bottom:16px; }} .metric {{ background:#f7f9fc; border:1px solid var(--line); border-radius:12px; padding:14px; }} .metric small {{ color:var(--muted); display:block; margin-bottom:6px; }} .metric strong {{ font-size:1.35rem; }} .month-filter {{ margin-bottom:16px; }} .month-filter label {{ display:block; }} .records {{ display:grid; gap:10px; margin-top:18px; }} .record {{ display:flex; justify-content:space-between; align-items:center; gap:12px; border:1px solid var(--line); border-radius:12px; padding:13px; }} .record small {{ color:var(--muted); display:block; margin-top:4px; }} .delete {{ background:#fff1f2; color:var(--red); padding:8px 10px; }} @media(max-width:760px) {{ .topbar,.record {{ align-items:stretch; flex-direction:column; }} .layout {{ grid-template-columns:1fr; }} .nav a,.logout {{ text-align:center; }} }}
</style></head><body><main class="container">
<header class="topbar"><div class="brand">Cuentita</div><nav class="nav"><a href="/menu">Menú</a><a href="/dashboard">Gastos</a><a class="active" href="{path}">{title}</a><button class="logout" onclick="logout()">Salir</button></nav></header>
<section class="layout"><section class="card"><h1>{title}</h1><p class="intro">{intro}</p><form id="entryForm">{fields}<button type="submit">Guardar {singular}</button></form><div id="status" class="status"></div></section><section class="card">{month_control}<div class="metric-grid">{metrics}</div><div class="chart-wrap"><canvas id="mainChart"></canvas></div><div id="records" class="records"></div></section></section>
</main><script>
const endpoint='{endpoint}'; const comparisonEndpoint='{comparison_endpoint}'; const isIncome={is_income}; let chart; let allData=[]; let expenseData=[];
const money=v=>new Intl.NumberFormat('es-AR',{{style:'currency',currency:'ARS'}}).format(Number(v||0));
function csrfToken(){{const cookie=document.cookie.split('; ').find(item=>item.startsWith('csrf_token='));return cookie?decodeURIComponent(cookie.slice('csrf_token='.length)):'';}}
function api(url,options={{}}){{return fetch(url,{{...options,credentials:'same-origin',headers:{{'Content-Type':'application/json','Accept':'application/json','X-CSRF-Token':csrfToken(),...(options.headers||{{}})}}}})}}
function logout(){{fetch('/logout',{{method:'POST',headers:{{'X-CSRF-Token':csrfToken()}}}}).finally(()=>location.href='/login');}}
 function monthKey(value){{const date=new Date(value);return `${{date.getFullYear()}}-${{String(date.getMonth()+1).padStart(2,'0')}}`;}}
 function filtered(data){{const month=document.getElementById('monthFilter')?.value;return month?data.filter(item=>monthKey(item.fecha)===month):data;}}
 function render(data,expenses){{
 const total=data.reduce((sum,item)=>sum+Number(item.monto||0),0); document.getElementById('total').textContent=money(total); document.getElementById('count').textContent=data.length;
 let labels=data.map(item=>item.{label}); let values=data.map(item=>Number(item.monto||0)); let datasets=[{{label:'Monto',data:values,backgroundColor:'{color}'}}];
 if(isIncome){{const spent=expenses.reduce((sum,item)=>sum+Number(item.monto||0),0);document.getElementById('spent').textContent=money(spent);document.getElementById('balance').textContent=money(total-spent);labels=['Ingresos','Gastos'];values=[total,spent];datasets=[{{label:'Comparación mensual',data:values,backgroundColor:['#16805b','#c2414d']}}];}}
 if(chart) chart.destroy(); chart=new Chart(document.getElementById('mainChart'),{{type:'bar',data:{{labels,datasets}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:value=>money(value)}}}}}}}}}});
 const records=document.getElementById('records'); records.innerHTML=''; if(!data.length){{records.innerHTML='<div class="record">Todavía no hay registros.</div>';return;}} data.forEach(item=>{{const row=document.createElement('div');row.className='record'; const text=document.createElement('div');text.innerHTML=`<strong>${{item.{label}}}</strong><small>${{new Date(item.fecha).toLocaleDateString('es-AR')}}</small>`; const amount=document.createElement('strong');amount.textContent=money(item.monto); const del=document.createElement('button');del.className='delete';del.textContent='Eliminar';del.onclick=async()=>{{await api(`${{endpoint}}/${{item.id}}`,{{method:'DELETE'}});load();}};row.append(text,amount,del);records.appendChild(row);}}); }}
async function load(){{const responses=await Promise.all([api(endpoint),...(comparisonEndpoint?[api(comparisonEndpoint)]:[])]);if(!responses[0].ok){{location.href='/login';return;}}allData=await responses[0].json();expenseData=comparisonEndpoint?await responses[1].json():[];if(isIncome&&!document.getElementById('monthFilter').value){{document.getElementById('monthFilter').value=monthKey(new Date());}}render(filtered(allData),filtered(expenseData));}} document.getElementById('monthFilter')?.addEventListener('change',()=>render(filtered(allData),filtered(expenseData))); document.getElementById('entryForm').addEventListener('submit',async event=>{{event.preventDefault();const form=new FormData(event.currentTarget);const payload={{'{payload1}':form.get('{input1}'),'{payload2}':Number(form.get('{input2}')){extra}}};const res=await api(endpoint,{{method:'POST',body:JSON.stringify(payload)}});const status=document.getElementById('status');if(!res.ok){{const error=await res.json();status.textContent=error.detail||'No se pudo guardar';status.style.color='var(--red)';return;}}status.textContent='Guardado correctamente';status.style.color='var(--green)';event.currentTarget.reset();load();}});load();
</script></body></html>
"""


@router.get("/ingresos", response_class=HTMLResponse)
def ingresos_page():
    return HTMLResponse((FRONTEND_DIR / "templates" / "ingresos.html").read_text(encoding="utf-8"))
    return HTMLResponse(SHELL.format(title="Ingresos", path="/ingresos", intro="Registra el dinero que entra y comparalo con tus gastos del mismo mes.", singular="ingreso", endpoint="/api/ingresos", comparison_endpoint="/gastos", is_income="true", label="motivo", input1="motivo", input2="monto", payload1="motivo", payload2="monto", extra="", color="#16805b", month_control='<div class="month-filter"><label for="monthFilter">Mes a consultar<input id="monthFilter" type="month"></label></div>', fields='<label>Motivo<input name="motivo" placeholder="Ej: Sueldo, venta, regalo" required></label><label>Monto<input name="monto" type="number" min="0.01" step="0.01" placeholder="0,00" required></label>', metrics='<div class="metric"><small>Total ingresado</small><strong id="total">$0</strong></div><div class="metric"><small>Total gastado</small><strong id="spent">$0</strong></div><div class="metric"><small>Saldo del mes</small><strong id="balance">$0</strong></div><div class="metric"><small>Ingresos registrados</small><strong id="count">0</strong></div>'))


@router.get("/inversiones", response_class=HTMLResponse)
def inversiones_page():
    return HTMLResponse((FRONTEND_DIR / "templates" / "inversiones.html").read_text(encoding="utf-8"))
    return HTMLResponse(INVESTMENT_PAGE)
