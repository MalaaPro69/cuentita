from sqlalchemy.orm import Session
from app.models.db_models import Gasto
from app.schemas.pydantic_schemas import GastoCreate, ResumenCategoria


def crear_gasto(db: Session, gasto: GastoCreate, usuario_id: int):
    nuevo_gasto = Gasto(
        monto=gasto.monto,
        descripcion=gasto.descripcion,
        categoria=gasto.categoria or "General",
        usuario_id=usuario_id
    )
    db.add(nuevo_gasto)
    db.commit()
    db.refresh(nuevo_gasto)
    return nuevo_gasto


def obtener_gastos(db: Session, usuario_id: int):
    return db.query(Gasto).filter(Gasto.usuario_id == usuario_id).all()


def listar_gastos_usuario(usuario_id: int, db: Session):
    return db.query(Gasto).filter(Gasto.usuario_id == usuario_id).order_by(Gasto.fecha.desc()).all()


def obtener_resumen_por_categoria(usuario_id: int, db: Session):
    gastos = listar_gastos_usuario(usuario_id, db)
    resumen = {}

    for gasto in gastos:
        categoria = gasto.categoria or "General"
        if categoria not in resumen:
            resumen[categoria] = {"categoria": categoria, "total": 0.0, "cantidad": 0}
        resumen[categoria]["total"] += float(gasto.monto)
        resumen[categoria]["cantidad"] += 1

    return [ResumenCategoria(**datos) for datos in resumen.values()]


def eliminar_gasto(db: Session, gasto_id: int, usuario_id: int):
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id, Gasto.usuario_id == usuario_id).first()
    if gasto:
        db.delete(gasto)
        db.commit()
        return True
    return False