from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Index, UniqueConstraint, text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    color_hex = Column(String, nullable=False, default="#718096")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    auth_version = Column(Integer, nullable=False, default=0, server_default=text("0"))

    gastos = relationship("Gasto", back_populates="usuario")
    ingresos = relationship("Ingreso", back_populates="usuario")
    inversiones = relationship("Inversion", back_populates="usuario")
    gastos_fijos = relationship("GastoFijo", back_populates="usuario")
    ingresos_fijos = relationship("IngresoFijo", back_populates="usuario")


class Gasto(Base):
    __tablename__ = "gastos"
    __table_args__ = (Index("ix_gastos_usuario_fecha", "usuario_id", "fecha"),)

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Float, nullable=False)
    descripcion = Column(String, nullable=False)
    categoria = Column(String, default="General")
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    gasto_fijo_id = Column(Integer, ForeignKey("gastos_fijos.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="gastos")


class Presupuesto(Base):
    __tablename__ = "presupuestos"
    __table_args__ = (
        UniqueConstraint("usuario_id", "categoria", name="uq_presupuestos_usuario_categoria"),
    )

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(50), nullable=False)
    monto_maximo = Column(Float, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)


class Ingreso(Base):
    __tablename__ = "ingresos"
    __table_args__ = (Index("ix_ingresos_usuario_fecha", "usuario_id", "fecha"),)

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Float, nullable=False)
    motivo = Column(String, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    ingreso_fijo_id = Column(Integer, ForeignKey("ingresos_fijos.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="ingresos")


class GastoFijo(Base):
    __tablename__ = "gastos_fijos"
    __table_args__ = (Index("ix_gastos_fijos_usuario_activo_dia", "usuario_id", "activo", "dia_mes"),)

    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String, nullable=False)
    categoria = Column(String, nullable=False, default="General")
    monto = Column(Float, nullable=False)
    dia_mes = Column(Integer, nullable=False, default=1)
    activo = Column(Boolean, nullable=False, default=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="gastos_fijos")
    movimientos = relationship("Gasto", backref="gasto_fijo")


class IngresoFijo(Base):
    __tablename__ = "ingresos_fijos"
    __table_args__ = (Index("ix_ingresos_fijos_usuario_activo_dia", "usuario_id", "activo", "dia_mes"),)

    id = Column(Integer, primary_key=True, index=True)
    motivo = Column(String, nullable=False)
    monto = Column(Float, nullable=False)
    dia_mes = Column(Integer, nullable=False, default=1)
    activo = Column(Boolean, nullable=False, default=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="ingresos_fijos")
    movimientos = relationship("Ingreso", backref="ingreso_fijo")


class Inversion(Base):
    __tablename__ = "inversiones"
    __table_args__ = (Index("ix_inversiones_usuario_fecha", "usuario_id", "fecha"),)

    id = Column(Integer, primary_key=True, index=True)
    activo = Column(String, nullable=False)
    simbolo = Column(String, nullable=True)
    monto = Column(Float, nullable=False)
    monto_invertido = Column(Float, nullable=False, default=0.0)
    cantidad = Column(Float, nullable=False, default=1.0)
    precio_actual = Column(Float, nullable=False, default=0.0)
    rendimiento = Column(Float, nullable=False, default=0.0)
    moneda_inversion = Column(String(3), nullable=False, default="USD", server_default="USD")
    monto_invertido_original = Column(Float, nullable=False, default=0.0, server_default="0")
    tipo_cambio_ars_usd = Column(Float, nullable=False, default=1.0, server_default="1")
    variacion_24h = Column(Float, nullable=True)
    cotizacion_actualizada = Column(DateTime, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="inversiones")


class SimboloActivo(Base):
    __tablename__ = "simbolos_activos"
    __table_args__ = (
        UniqueConstraint("nombre_normalizado", name="uq_simbolos_activos_nombre_normalizado"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre_normalizado = Column(String(150), nullable=False)
    simbolo = Column(String(20), nullable=True)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_rate_time", "rate_key", "attempted_at"),)

    id = Column(Integer, primary_key=True, index=True)
    rate_key = Column(String(64), nullable=False)
    attempted_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    __table_args__ = (
        Index("ix_account_tokens_user_purpose_created", "usuario_id", "purpose", "created_at"),
        Index("ix_account_tokens_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    purpose = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)