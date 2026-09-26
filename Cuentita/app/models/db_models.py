from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
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

    gastos = relationship("Gasto", back_populates="usuario")
    ingresos = relationship("Ingreso", back_populates="usuario")
    inversiones = relationship("Inversion", back_populates="usuario")
    gastos_fijos = relationship("GastoFijo", back_populates="usuario")
    ingresos_fijos = relationship("IngresoFijo", back_populates="usuario")


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Float, nullable=False)
    descripcion = Column(String, nullable=False)
    categoria = Column(String, default="General")
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    gasto_fijo_id = Column(Integer, ForeignKey("gastos_fijos.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="gastos")


class Ingreso(Base):
    __tablename__ = "ingresos"

    id = Column(Integer, primary_key=True, index=True)
    monto = Column(Float, nullable=False)
    motivo = Column(String, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    ingreso_fijo_id = Column(Integer, ForeignKey("ingresos_fijos.id"), nullable=True)

    usuario = relationship("Usuario", back_populates="ingresos")


class GastoFijo(Base):
    __tablename__ = "gastos_fijos"

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

    id = Column(Integer, primary_key=True, index=True)
    activo = Column(String, nullable=False)
    simbolo = Column(String, nullable=True)
    monto = Column(Float, nullable=False)
    monto_invertido = Column(Float, nullable=False, default=0.0)
    cantidad = Column(Float, nullable=False, default=1.0)
    precio_actual = Column(Float, nullable=False, default=0.0)
    rendimiento = Column(Float, nullable=False, default=0.0)
    variacion_24h = Column(Float, nullable=True)
    cotizacion_actualizada = Column(DateTime, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    usuario = relationship("Usuario", back_populates="inversiones")