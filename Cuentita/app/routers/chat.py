from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.schemas.pydantic_schemas import MensajeChat, GastoResponse
from app.services.auth_service import get_current_user
from app.models.db_models import Usuario
from app.controllers import chat_controller

router = APIRouter(prefix="/chat", tags=["Chat & IA"])

@router.post("/procesar", response_model=GastoResponse)
def procesar_mensaje(
    mensaje_data: MensajeChat,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(get_current_user)
):
    return chat_controller.procesar_y_guardar_gasto(mensaje_data.mensaje, usuario_actual, db)