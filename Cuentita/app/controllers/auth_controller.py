from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.db_models import Usuario
from app.schemas.pydantic_schemas import UsuarioCreate
from app.services.auth_service import create_access_token
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def crear_usuario(db: Session, usuario: UsuarioCreate):
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    nuevo_usuario = Usuario(
        email=usuario.email,
        hashed_password=hash_password(usuario.password),
        nombre=usuario.nombre
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


def registrar_nuevo_usuario(usuario: UsuarioCreate, db: Session):
    return crear_usuario(db, usuario)


def autenticar_usuario(email: str, password: str, db: Session):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not verify_password(password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    access_token = create_access_token({"sub": usuario.email})
    return {"access_token": access_token, "token_type": "bearer"}