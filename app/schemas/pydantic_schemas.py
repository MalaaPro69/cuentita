from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Literal, Optional
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


class PresupuestoCreate(BaseModel):
    categoria: str = Field(min_length=1, max_length=50)
    monto_maximo: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("categoria")
    @classmethod
    def category_must_not_be_blank(cls, categoria: str) -> str:
        categoria = categoria.strip()
        if not categoria:
            raise ValueError("La categoría no puede estar vacía")
        return categoria


class PresupuestoResponse(BaseModel):
    id: int
    categoria: str
    monto_maximo: float
    usuario_id: int

    class Config:
        from_attributes = True


class PresupuestoResumen(PresupuestoResponse):
    gastado: float
    porcentaje: float
    estado: str


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
    activo: str = Field(min_length=1, max_length=100)
    simbolo: Optional[str] = None
    monto: float
    monto_invertido: float = 0.0
    cantidad: float = 1.0
    precio_actual: float = 0.0
    rendimiento: float = 0.0
    moneda_inversion: Literal["USD", "ARS"] = "USD"
    monto_invertido_original: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    tipo_cambio_ars_usd: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)

    @field_validator("activo")
    @classmethod
    def normalize_asset_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre del activo no puede estar vacío")
        return value

    @model_validator(mode="after")
    def validate_investment_currency(self):
        if self.moneda_inversion == "ARS" and self.tipo_cambio_ars_usd is None:
            raise ValueError("El tipo de cambio ARS/USD es obligatorio para inversiones en pesos")
        if (
            self.moneda_inversion == "ARS"
            and self.monto_invertido_original is not None
            and self.monto_invertido_original <= 0
        ):
            raise ValueError("El total invertido en ARS debe ser mayor que cero")
        return self


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
    mensaje: str = Field(min_length=1, max_length=2000)

    @field_validator("mensaje")
    @classmethod
    def message_must_not_be_blank(cls, mensaje: str) -> str:
        mensaje = mensaje.strip()
        if not mensaje:
            raise ValueError("El mensaje no puede estar vacío")
        return mensaje


MensajeChat = ChatMessage


class ChatProcessResponse(BaseModel):
    es_gasto: bool
    respuesta_chat: str
    gasto: Optional[GastoResponse] = None