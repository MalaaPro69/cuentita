from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from app.database.connection import engine, Base, get_db
from app.models import db_models
from app.routers import auth, chat, gastos, finanzas

# Crear las tablas
Base.metadata.create_all(bind=engine)


def actualizar_esquema_inversiones():
    columnas_por_tabla = {
        "gastos": {"gasto_fijo_id": "INTEGER"},
        "ingresos": {"ingreso_fijo_id": "INTEGER"},
        "inversiones": {
            "simbolo": "VARCHAR(40)",
            "monto_invertido": "FLOAT NOT NULL DEFAULT 0.0",
            "cantidad": "FLOAT NOT NULL DEFAULT 1.0",
            "precio_actual": "FLOAT NOT NULL DEFAULT 0.0",
            "variacion_24h": "FLOAT",
            "cotizacion_actualizada": "DATETIME",
        },
    }
    with engine.begin() as connection:
        for tabla, nuevas_columnas in columnas_por_tabla.items():
            columnas = {columna["name"] for columna in inspect(engine).get_columns(tabla)}
            for nombre, definicion in nuevas_columnas.items():
                if nombre not in columnas:
                    connection.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}"))
            connection.execute(text("UPDATE inversiones SET monto_invertido = monto WHERE monto_invertido = 0"))


actualizar_esquema_inversiones()

app = FastAPI(title="Backend App Gastos Personales")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicializar categorías por defecto
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    categorias_defecto = [
        ("Alimentación", "#e53e3e"),
        ("Transporte", "#3182ce"),
        ("Servicios", "#dd6b20"),
        ("Entretenimiento", "#805ad5"),
        ("Salud", "#38a169"),
        ("Otros", "#718096")
    ]
    for nombre, color in categorias_defecto:
        if not db.query(db_models.Categoria).filter(db_models.Categoria.nombre == nombre).first():
            db.add(db_models.Categoria(nombre=nombre, color_hex=color))
    db.commit()

# Incluir los Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(gastos.router)
app.include_router(finanzas.router)