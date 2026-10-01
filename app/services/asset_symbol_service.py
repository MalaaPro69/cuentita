import unicodedata
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import Inversion, SimboloActivo
from app.services.gemini_service import GeminiServiceError, identificar_simbolo_activo


@dataclass(frozen=True)
class SymbolResolution:
    symbol: str | None
    status: str


def normalize_asset_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name).casefold()
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    normalized = "".join(char if char.isalnum() or char.isspace() else " " for char in without_accents)
    return " ".join(normalized.split())


def _store_symbol(db: Session, normalized_name: str, symbol: str | None) -> SimboloActivo:
    association = SimboloActivo(
        nombre_normalizado=normalized_name,
        simbolo=symbol,
    )
    db.add(association)
    try:
        db.commit()
        return association
    except IntegrityError:
        db.rollback()
        cached = db.query(SimboloActivo).filter(
            SimboloActivo.nombre_normalizado == normalized_name
        ).first()
        if not cached:
            raise
        return cached
    except Exception:
        db.rollback()
        raise


def resolve_asset_symbol(db: Session, name: str) -> SymbolResolution:
    normalized_name = normalize_asset_name(name)
    if not normalized_name:
        raise ValueError("El nombre del activo no puede estar vacío")

    cached = db.query(SimboloActivo).filter(
        SimboloActivo.nombre_normalizado == normalized_name
    ).first()
    if cached:
        return SymbolResolution(cached.simbolo, "found" if cached.simbolo else "not_found")

    legacy_symbols = {
        symbol
        for (symbol,) in db.query(Inversion.simbolo).filter(
            func.lower(Inversion.activo) == name.strip().casefold(),
            Inversion.simbolo.is_not(None),
        ).distinct().all()
        if symbol
    }
    if len(legacy_symbols) == 1:
        association = _store_symbol(db, normalized_name, legacy_symbols.pop())
        return SymbolResolution(association.simbolo, "found")

    result = identificar_simbolo_activo(name)
    association = _store_symbol(db, normalized_name, result.simbolo)
    return SymbolResolution(association.simbolo, "found" if association.simbolo else "not_found")


__all__ = ["GeminiServiceError", "SymbolResolution", "resolve_asset_symbol"]
