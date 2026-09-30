from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime

# ================================
# ESQUEMAS DE AUTENTICACIÓN / USUARIOS
# ================================

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str = Field(min_length=12)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes")
        return password


class UsuarioResponse(UsuarioBase):
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ================================
# ESQUEMAS DE GASTOS
# ================================

class GastoBase(BaseModel):
    monto: float
    descripcion: str
    categoria: Optional[str] = None


class GastoCreate(GastoBase):
    pass


class GastoResponse(GastoBase):
    id: int
    fecha: datetime
    usuario_id: int

    class Config:
        from_attributes = True


class ResumenCategoria(BaseModel):
    categoria: str
    total: float
    cantidad: int


class IngresoCreate(BaseModel):
    monto: float
    motivo: str


class IngresoResponse(IngresoCreate):
    id: int
    fecha: datetime
    usuario_id: int

    class Config:
        from_attributes = True


class GastoFijoCreate(BaseModel):
    descripcion: str
    categoria: str = "General"
    monto: float
    dia_mes: int = 1
    activo: bool = True


class GastoFijoResponse(GastoFijoCreate):
    id: int
    usuario_id: int

    class Config:
        from_attributes = True


class IngresoFijoCreate(BaseModel):
    motivo: str
    monto: float
    dia_mes: int = 1
    activo: bool = True


class IngresoFijoResponse(IngresoFijoCreate):
    id: int
    usuario_id: int

    class Config:
        from_attributes = True


class InversionCreate(BaseModel):
    activo: str
    simbolo: Optional[str] = None
    monto: float
    monto_invertido: float = 0.0
    cantidad: float = 1.0
    precio_actual: float = 0.0
    rendimiento: float = 0.0


class InversionResponse(InversionCreate):
    id: int
    fecha: datetime
    usuario_id: int
    variacion_24h: Optional[float] = None
    cotizacion_actualizada: Optional[datetime] = None

    class Config:
        from_attributes = True


# ================================
# ESQUEMAS DE CHAT / IA
# ================================

class ChatMessage(BaseModel):
    mensaje: str


MensajeChat = ChatMessage


class ChatResponse(BaseModel):
    respuesta: str