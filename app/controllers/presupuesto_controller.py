from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import Gasto, Presupuesto


def listar_presupuestos(db: Session, usuario_id: int, ahora: datetime | None = None):
    ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)
    inicio_mes = datetime(ahora.year, ahora.month, 1)
    inicio_mes_siguiente = datetime(
        ahora.year + (ahora.month == 12),
        ahora.month % 12 + 1,
        1,
    )
    gastos_por_categoria = dict(
        db.query(Gasto.categoria, func.sum(Gasto.monto))
        .filter(
            Gasto.usuario_id == usuario_id,
            Gasto.fecha >= inicio_mes,
            Gasto.fecha < inicio_mes_siguiente,
        )
        .group_by(Gasto.categoria)
        .all()
    )

    presupuestos = (
        db.query(Presupuesto)
        .filter(Presupuesto.usuario_id == usuario_id)
        .order_by(Presupuesto.categoria)
        .all()
    )
    resultados = []
    for presupuesto in presupuestos:
        gastado = float(gastos_por_categoria.get(presupuesto.categoria) or 0)
        porcentaje = gastado / presupuesto.monto_maximo * 100
        estado = "superado" if porcentaje >= 100 else "cerca" if porcentaje >= 80 else "normal"
        resultados.append({
            "id": presupuesto.id,
            "categoria": presupuesto.categoria,
            "monto_maximo": presupuesto.monto_maximo,
            "usuario_id": presupuesto.usuario_id,
            "gastado": gastado,
            "porcentaje": porcentaje,
            "estado": estado,
        })
    return resultados


def crear_presupuesto(db: Session, categoria: str, monto_maximo: float, usuario_id: int):
    presupuesto = Presupuesto(
        categoria=categoria,
        monto_maximo=monto_maximo,
        usuario_id=usuario_id,
    )
    db.add(presupuesto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existente = db.query(Presupuesto).filter(
            Presupuesto.usuario_id == usuario_id,
            Presupuesto.categoria == categoria,
        ).first()
        if existente:
            return None
        raise
    db.refresh(presupuesto)
    return presupuesto


def actualizar_presupuesto(
    db: Session,
    presupuesto_id: int,
    categoria: str,
    monto_maximo: float,
    usuario_id: int,
):
    presupuesto = db.query(Presupuesto).filter(
        Presupuesto.id == presupuesto_id,
        Presupuesto.usuario_id == usuario_id,
    ).first()
    if not presupuesto:
        return None

    presupuesto.categoria = categoria
    presupuesto.monto_maximo = monto_maximo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(presupuesto)
    return presupuesto


def eliminar_presupuesto(db: Session, presupuesto_id: int, usuario_id: int) -> bool:
    presupuesto = db.query(Presupuesto).filter(
        Presupuesto.id == presupuesto_id,
        Presupuesto.usuario_id == usuario_id,
    ).first()
    if not presupuesto:
        return False
    db.delete(presupuesto)
    db.commit()
    return True
