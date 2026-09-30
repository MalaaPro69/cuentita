from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database.connection import get_db
from app.models import db_models
from app.routers import auth, chat, gastos, finanzas
from app.security import csrf_protection

app = FastAPI(title="Backend App Gastos Personales")
app.middleware("http")(csrf_protection)
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