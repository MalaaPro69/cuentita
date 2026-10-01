from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.schemas.pydantic_schemas import GastoCreate, GastoFijoCreate, GastoFijoResponse, GastoResponse, ResumenCategoria
from app.services.auth_service import get_current_user
from app.models.db_models import Usuario
from app.controllers import finanzas_controller, gastos_controller

router = APIRouter(prefix="/gastos", tags=["Gastos y Estadísticas"])


@router.post("", response_model=GastoResponse)
def crear_gasto(
    gasto: GastoCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user)
):
    return gastos_controller.crear_gasto(db, gasto, usuario_actual.id)


@router.get("", response_model=List[GastoResponse])
def obtener_gastos(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user)
):
    finanzas_controller.generar_gastos_fijos_del_mes(db, usuario_actual.id)
    return gastos_controller.listar_gastos_usuario(usuario_actual.id, db)


@router.post("/fijos", response_model=GastoFijoResponse)
def crear_gasto_fijo(gasto: GastoFijoCreate, db: Session = Depends(get_db), usuario_actual: Usuario = Depends(get_current_user)):
    return finanzas_controller.crear_gasto_fijo(db, gasto, usuario_actual.id)


@router.get("/fijos", response_model=List[GastoFijoResponse])
def obtener_gastos_fijos(db: Session = Depends(get_db), usuario_actual: Usuario = Depends(get_current_user)):
    return finanzas_controller.listar_gastos_fijos(db, usuario_actual.id)


@router.put("/fijos/{fijo_id}", response_model=GastoFijoResponse)
def editar_gasto_fijo(fijo_id: int, gasto: GastoFijoCreate, db: Session = Depends(get_db), usuario_actual: Usuario = Depends(get_current_user)):
    registro = finanzas_controller.actualizar_gasto_fijo(db, fijo_id, gasto, usuario_actual.id)
    if not registro:
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    return registro


@router.delete("/fijos/{fijo_id}")
def eliminar_gasto_fijo(fijo_id: int, db: Session = Depends(get_db), usuario_actual: Usuario = Depends(get_current_user)):
    if not finanzas_controller.eliminar_gasto_fijo(db, fijo_id, usuario_actual.id):
        raise HTTPException(status_code=404, detail="Gasto fijo no encontrado")
    return {"ok": True}


@router.get("/resumen", response_model=List[ResumenCategoria])
def resumen_gastos(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user)
):
    return gastos_controller.obtener_resumen_por_categoria(usuario_actual.id, db)


@router.get("/resumen-categorias", response_model=List[ResumenCategoria])
def resumen_categorias(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user)
):
    return gastos_controller.obtener_resumen_por_categoria(usuario_actual.id, db)


@router.delete("/{gasto_id}", status_code=status.HTTP_200_OK)
def borrar_gasto(
    gasto_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user)
):
    eliminado = gastos_controller.eliminar_gasto(db, gasto_id, usuario_actual.id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado")
    return {"ok": True, "message": "Gasto eliminado"}