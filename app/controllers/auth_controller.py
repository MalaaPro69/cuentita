import hashlib
import hmac
import ipaddress
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import HTTPException, Request, status
from app.config import settings
from app.models.db_models import AccountToken, LoginAttempt, Usuario
from app.schemas.pydantic_schemas import UsuarioCreate
from app.services.email_service import send_account_email
from app.services.auth_service import create_access_token
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def crear_usuario(db: Session, usuario: UsuarioCreate):
    email = usuario.email.strip().lower()
    usuario_existente = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    nuevo_usuario = Usuario(
        email=email,
        hashed_password=hash_password(usuario.password),
        nombre=usuario.nombre,
        is_verified=False,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


def registrar_nuevo_usuario(usuario: UsuarioCreate, db: Session):
    nuevo_usuario = crear_usuario(db, usuario)
    _enviar_verificacion(nuevo_usuario, db)
    return nuevo_usuario


def _emitir_token_cuenta(usuario: Usuario, purpose: str, duracion: timedelta, db: Session) -> str | None:
    ahora = datetime.utcnow()
    db.query(AccountToken).filter(AccountToken.expires_at < ahora - timedelta(days=30)).delete()
    reciente = db.query(AccountToken).filter(
        AccountToken.usuario_id == usuario.id,
        AccountToken.purpose == purpose,
        AccountToken.created_at >= ahora - timedelta(minutes=1),
    ).first()
    if reciente:
        return None

    db.query(AccountToken).filter(
        AccountToken.usuario_id == usuario.id,
        AccountToken.purpose == purpose,
        AccountToken.used_at.is_(None),
    ).update({"used_at": ahora}, synchronize_session=False)
    token = secrets.token_urlsafe(32)
    db.add(AccountToken(
        usuario_id=usuario.id,
        purpose=purpose,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=ahora + duracion,
    ))
    db.commit()
    return token


def _enviar_verificacion(usuario: Usuario, db: Session) -> None:
    token = _emitir_token_cuenta(usuario, "verify", timedelta(hours=24), db)
    if not token:
        return
    link = f"{settings.PUBLIC_BASE_URL}/confirmar-email#token={token}"
    send_account_email(
        usuario.email,
        "Confirma tu correo de Cuentita",
        f"Abre este enlace para verificar tu correo (válido por 24 horas):\n\n{link}\n",
    )


def reenviar_verificacion(email: str, db: Session) -> None:
    usuario = db.query(Usuario).filter(Usuario.email == email.strip().lower()).first()
    if usuario and usuario.is_active and not usuario.is_verified:
        _enviar_verificacion(usuario, db)


def solicitar_recuperacion(email: str, db: Session) -> None:
    usuario = db.query(Usuario).filter(Usuario.email == email.strip().lower()).first()
    if not usuario or not usuario.is_active:
        return

    token = _emitir_token_cuenta(usuario, "reset", timedelta(minutes=30), db)
    if not token:
        return
    link = f"{settings.PUBLIC_BASE_URL}/restablecer#token={token}"
    send_account_email(
        usuario.email,
        "Restablece tu contraseña de Cuentita",
        f"Abre este enlace para elegir una nueva contraseña (válido por 30 minutos):\n\n{link}\n",
    )


def _obtener_token_cuenta(token: str, purpose: str, db: Session):
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    ahora = datetime.utcnow()
    registro = db.query(AccountToken).filter(
        AccountToken.token_hash == digest,
        AccountToken.purpose == purpose,
        AccountToken.used_at.is_(None),
        AccountToken.expires_at > ahora,
    ).first()
    if not registro:
        raise HTTPException(status_code=400, detail="El enlace no es válido o ya venció")
    return registro, db.query(Usuario).filter(Usuario.id == registro.usuario_id).first(), ahora


def _consumir_token_cuenta(registro: AccountToken, ahora: datetime, db: Session) -> None:
    actualizado = db.query(AccountToken).filter(
        AccountToken.id == registro.id,
        AccountToken.used_at.is_(None),
        AccountToken.expires_at > ahora,
    ).update({"used_at": ahora}, synchronize_session=False)
    if actualizado != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="El enlace no es válido o ya venció")


def confirmar_email(token: str, db: Session) -> None:
    registro, usuario, ahora = _obtener_token_cuenta(token, "verify", db)
    if not usuario or not usuario.is_active:
        raise HTTPException(status_code=400, detail="El enlace no es válido o ya venció")
    _consumir_token_cuenta(registro, ahora, db)
    usuario.is_verified = True
    db.commit()


def restablecer_contrasena(token: str, password: str, db: Session) -> None:
    registro, usuario, ahora = _obtener_token_cuenta(token, "reset", db)
    if not usuario or not usuario.is_active:
        raise HTTPException(status_code=400, detail="El enlace no es válido o ya venció")
    datos = UsuarioCreate(email=usuario.email, password=password, nombre=usuario.nombre)
    _consumir_token_cuenta(registro, ahora, db)
    usuario.hashed_password = hash_password(datos.password)
    usuario.auth_version += 1
    db.commit()


def _rate_key(scope: str, value: str) -> str:
    message = f"{scope}:{value.strip().lower()}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


def get_client_ip(request: Request) -> str:
    remote_address = request.client.host if request.client else "unknown"
    try:
        remote_ip = ipaddress.ip_address(remote_address).compressed
    except ValueError:
        return remote_address

    trusted_proxies = set(settings.TRUSTED_PROXY_IPS)
    if remote_ip not in trusted_proxies:
        return remote_ip

    forwarded_for = request.headers.get("x-forwarded-for", "")
    for address in reversed(forwarded_for.split(",")):
        try:
            forwarded_ip = ipaddress.ip_address(address.strip()).compressed
        except ValueError:
            continue
        if forwarded_ip not in trusted_proxies:
            return forwarded_ip
    return remote_ip


def autenticar_usuario(email: str, password: str, db: Session, ip_address: str = "unknown"):
    email = email.strip().lower()
    ahora = datetime.utcnow()
    inicio_ventana = ahora - timedelta(minutes=15)
    email_ip_key = _rate_key("email-ip", f"{email}|{ip_address}")
    ip_key = _rate_key("ip", ip_address)

    db.query(LoginAttempt).filter(LoginAttempt.attempted_at < ahora - timedelta(days=1)).delete()
    for rate_key, max_intentos in ((email_ip_key, 5), (ip_key, 30)):
        intentos = db.query(LoginAttempt).filter(
            LoginAttempt.rate_key == rate_key,
            LoginAttempt.attempted_at >= inicio_ventana,
        ).count()
        if intentos >= max_intentos:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Espera 15 minutos antes de volver a probar.",
                headers={"Retry-After": "900"},
            )

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    password_valida = len(password.encode("utf-8")) <= 72 and usuario and verify_password(password, usuario.hashed_password)
    if not password_valida:
        db.add_all([
            LoginAttempt(rate_key=email_ip_key, attempted_at=ahora),
            LoginAttempt(rate_key=ip_key, attempted_at=ahora),
        ])
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    db.query(LoginAttempt).filter(LoginAttempt.rate_key == email_ip_key).delete()
    db.commit()
    if not usuario.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos")
    if not usuario.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verifica tu correo antes de iniciar sesión")

    access_token = create_access_token({"sub": usuario.email, "ver": usuario.auth_version})
    return {"access_token": access_token, "token_type": "bearer"}