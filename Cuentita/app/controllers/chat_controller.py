import os
from google import genai
from sqlalchemy.orm import Session

from app.models.db_models import Gasto, Usuario
from app.services.gemini_service import procesar_mensaje_gasto

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def responder_chat(mensaje: str, resumen_gastos: str = "") -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "tu_api_key_de_gemini_aqui":
        return "Respuesta de prueba (Configura tu GEMINI_API_KEY en el archivo .env para conectar Gemini IA)."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"Eres un asistente financiero personal llamado Cuentita. Ayudas al usuario a gestionar sus gastos de forma amable y concisa.\n"
        if resumen_gastos:
            prompt += f"Contexto de gastos del usuario: {resumen_gastos}\n"
        prompt += f"Usuario: {mensaje}"

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Error al procesar mensaje con la IA: {str(e)}"


def procesar_y_guardar_gasto(mensaje: str, usuario: Usuario, db: Session):
    resultado = procesar_mensaje_gasto(mensaje)
    descripcion = str(resultado.get("descripcion") or "Consulta del usuario").strip() or "Consulta del usuario"
    categoria = str(resultado.get("categoria") or "General")

    if not resultado.get("es_gasto", False):
        gasto = Gasto(
            monto=0.0,
            descripcion=descripcion,
            categoria=categoria,
            usuario_id=usuario.id
        )
        db.add(gasto)
        db.commit()
        db.refresh(gasto)
        return gasto

    gasto = Gasto(
        monto=float(resultado.get("monto", 0.0) or 0.0),
        descripcion=descripcion,
        categoria=categoria,
        usuario_id=usuario.id
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto