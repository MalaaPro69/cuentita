import logging
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
if APP_ENV not in {"development", "production"}:
    raise RuntimeError("APP_ENV debe ser 'development' o 'production'")

SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cuentita.db")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USERNAME)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TRUSTED_PROXY_IPS = tuple(
    address.strip()
    for address in os.getenv("TRUSTED_PROXY_IPS", "127.0.0.1,::1").split(",")
    if address.strip()
)

if APP_ENV == "production":
    if not SECRET_KEY or len(SECRET_KEY) < 32:
        raise RuntimeError("En producción configura SECRET_KEY con al menos 32 caracteres")
    if not DATABASE_URL.lower().startswith("postgresql+psycopg://"):
        raise RuntimeError("En producción DATABASE_URL debe usar PostgreSQL con el driver psycopg")
    if not SMTP_USERNAME or not SMTP_PASSWORD or not EMAIL_FROM:
        raise RuntimeError("En producción configura SMTP_USERNAME, SMTP_PASSWORD y EMAIL_FROM")
    if not PUBLIC_BASE_URL.startswith("https://"):
        raise RuntimeError("En producción PUBLIC_BASE_URL debe usar HTTPS")
elif not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(48)
    logging.warning("SECRET_KEY no configurada; se generó una clave temporal para desarrollo")


class Settings:
    APP_ENV: str = APP_ENV
    SECRET_KEY: str = SECRET_KEY
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DATABASE_URL: str = DATABASE_URL
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    SMTP_HOST: str = SMTP_HOST
    SMTP_PORT: int = SMTP_PORT
    SMTP_USERNAME: str = SMTP_USERNAME
    SMTP_PASSWORD: str = SMTP_PASSWORD
    EMAIL_FROM: str = EMAIL_FROM
    PUBLIC_BASE_URL: str = PUBLIC_BASE_URL
    TRUSTED_PROXY_IPS: tuple[str, ...] = TRUSTED_PROXY_IPS

settings = Settings()