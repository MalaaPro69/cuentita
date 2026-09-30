from sqlalchemy.orm import Session
from datetime import datetime
from calendar import monthrange
from app.models.db_models import Gasto, GastoFijo, Ingreso, IngresoFijo, Inversion
from app.schemas.pydantic_schemas import GastoFijoCreate, IngresoCreate, IngresoFijoCreate, InversionCreate
from app.services.market_data_service import obtener_cotizacion


def crear_ingreso(db: Session, ingreso: IngresoCreate, usuario_id: int):
    registro = Ingreso(**ingreso.model_dump(), usuario_id=usuario_id)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def listar_ingresos(db: Session, usuario_id: int):
    return db.query(Ingreso).filter(Ingreso.usuario_id == usuario_id).order_by(Ingreso.fecha.desc()).all()


def eliminar_ingreso(db: Session, ingreso_id: int, usuario_id: int):
    registro = db.query(Ingreso).filter(Ingreso.id == ingreso_id, Ingreso.usuario_id == usuario_id).first()
    if not registro:
        return False
    db.delete(registro)
    db.commit()
    return True


def listar_gastos_fijos(db: Session, usuario_id: int):
    return db.query(GastoFijo).filter(GastoFijo.usuario_id == usuario_id).order_by(GastoFijo.activo.desc(), GastoFijo.dia_mes).all()


def crear_gasto_fijo(db: Session, gasto: GastoFijoCreate, usuario_id: int):
    datos = gasto.model_dump()
    datos["dia_mes"] = max(1, min(gasto.dia_mes, 31))
    registro = GastoFijo(**datos, usuario_id=usuario_id)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def actualizar_gasto_fijo(db: Session, fijo_id: int, gasto: GastoFijoCreate, usuario_id: int):
    registro = db.query(GastoFijo).filter(GastoFijo.id == fijo_id, GastoFijo.usuario_id == usuario_id).first()
    if not registro:
        return None
    for campo, valor in gasto.model_dump().items():
        setattr(registro, campo, valor)
    registro.dia_mes = max(1, min(registro.dia_mes, 31))
    db.commit()
    db.refresh(registro)
    return registro


def eliminar_gasto_fijo(db: Session, fijo_id: int, usuario_id: int):
    registro = db.query(GastoFijo).filter(GastoFijo.id == fijo_id, GastoFijo.usuario_id == usuario_id).first()
    if not registro:
        return False
    db.delete(registro)
    db.commit()
    return True


def generar_gastos_fijos_del_mes(db: Session, usuario_id: int, ahora: datetime | None = None):
    ahora = ahora or datetime.utcnow()
    mes_inicio = datetime(ahora.year, ahora.month, 1)
    mes_siguiente = datetime(ahora.year + (ahora.month == 12), ahora.month % 12 + 1, 1)
    fijos = db.query(GastoFijo).filter(GastoFijo.usuario_id == usuario_id, GastoFijo.activo.is_(True)).all()
    creados = 0
    for fijo in fijos:
        existe = db.query(Gasto).filter(
            Gasto.usuario_id == usuario_id,
            Gasto.gasto_fijo_id == fijo.id,
            Gasto.fecha >= mes_inicio,
            Gasto.fecha < mes_siguiente,
        ).first()
        if existe:
            continue
        dia = min(fijo.dia_mes, monthrange(ahora.year, ahora.month)[1])
        db.add(Gasto(monto=fijo.monto, descripcion=fijo.descripcion, categoria=fijo.categoria, fecha=datetime(ahora.year, ahora.month, dia), usuario_id=usuario_id, gasto_fijo_id=fijo.id))
        creados += 1
    if creados:
        db.commit()
    return creados


def listar_ingresos_fijos(db: Session, usuario_id: int):
    return db.query(IngresoFijo).filter(IngresoFijo.usuario_id == usuario_id).order_by(IngresoFijo.activo.desc(), IngresoFijo.dia_mes).all()


def crear_ingreso_fijo(db: Session, ingreso: IngresoFijoCreate, usuario_id: int):
    datos = ingreso.model_dump()
    datos["dia_mes"] = max(1, min(ingreso.dia_mes, 31))
    registro = IngresoFijo(**datos, usuario_id=usuario_id)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def actualizar_ingreso_fijo(db: Session, fijo_id: int, ingreso: IngresoFijoCreate, usuario_id: int):
    registro = db.query(IngresoFijo).filter(IngresoFijo.id == fijo_id, IngresoFijo.usuario_id == usuario_id).first()
    if not registro:
        return None
    for campo, valor in ingreso.model_dump().items():
        setattr(registro, campo, valor)
    registro.dia_mes = max(1, min(registro.dia_mes, 31))
    db.commit()
    db.refresh(registro)
    return registro


def eliminar_ingreso_fijo(db: Session, fijo_id: int, usuario_id: int):
    registro = db.query(IngresoFijo).filter(IngresoFijo.id == fijo_id, IngresoFijo.usuario_id == usuario_id).first()
    if not registro:
        return False
    db.delete(registro)
    db.commit()
    return True


def generar_ingresos_fijos_del_mes(db: Session, usuario_id: int, ahora: datetime | None = None):
    ahora = ahora or datetime.utcnow()
    mes_inicio = datetime(ahora.year, ahora.month, 1)
    mes_siguiente = datetime(ahora.year + (ahora.month == 12), ahora.month % 12 + 1, 1)
    fijos = db.query(IngresoFijo).filter(IngresoFijo.usuario_id == usuario_id, IngresoFijo.activo.is_(True)).all()
    creados = 0
    for fijo in fijos:
        existe = db.query(Ingreso).filter(
            Ingreso.usuario_id == usuario_id,
            Ingreso.ingreso_fijo_id == fijo.id,
            Ingreso.fecha >= mes_inicio,
            Ingreso.fecha < mes_siguiente,
        ).first()
        if existe:
            continue
        dia = min(fijo.dia_mes, monthrange(ahora.year, ahora.month)[1])
        db.add(Ingreso(monto=fijo.monto, motivo=fijo.motivo, fecha=datetime(ahora.year, ahora.month, dia), usuario_id=usuario_id, ingreso_fijo_id=fijo.id))
        creados += 1
    if creados:
        db.commit()
    return creados


def crear_inversion(db: Session, inversion: InversionCreate, usuario_id: int):
    registro = Inversion(**inversion.model_dump(), usuario_id=usuario_id)
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def listar_inversiones(db: Session, usuario_id: int):
    return db.query(Inversion).filter(Inversion.usuario_id == usuario_id).order_by(Inversion.fecha.desc()).all()


def actualizar_inversion(db: Session, inversion_id: int, inversion: InversionCreate, usuario_id: int):
    registro = db.query(Inversion).filter(Inversion.id == inversion_id, Inversion.usuario_id == usuario_id).first()
    if not registro:
        return None
    for campo, valor in inversion.model_dump().items():
        setattr(registro, campo, valor)
    db.commit()
    db.refresh(registro)
    return registro


def actualizar_cotizaciones(db: Session, usuario_id: int):
    registros = listar_inversiones(db, usuario_id)
    resultados = []
    for registro in registros:
        if not registro.simbolo:
            resultados.append({"id": registro.id, "actualizada": False, "motivo": "Falta símbolo"})
            continue
        cotizacion = obtener_cotizacion(registro.simbolo)
        if not cotizacion:
            resultados.append({"id": registro.id, "actualizada": False, "motivo": "Activo no encontrado"})
            continue
        registro.precio_actual = cotizacion["precio_usd"]
        registro.monto = float(registro.cantidad or 0) * registro.precio_actual
        registro.variacion_24h = cotizacion.get("variacion_24h")
        registro.cotizacion_actualizada = datetime.utcnow()
        resultados.append({
            "id": registro.id,
            "actualizada": True,
            "precio_usd": registro.precio_actual,
            "variacion_24h": registro.variacion_24h,
            "proveedor": cotizacion["proveedor"],
        })
    db.commit()
    return resultados


def eliminar_inversion(db: Session, inversion_id: int, usuario_id: int):
    registro = db.query(Inversion).filter(Inversion.id == inversion_id, Inversion.usuario_id == usuario_id).first()
    if not registro:
        return False
    db.delete(registro)
    db.commit()
    return True
