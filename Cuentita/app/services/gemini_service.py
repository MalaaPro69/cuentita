import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def procesar_mensaje_gasto(mensaje: str) -> dict:
    """
    Analiza el texto ingresado por el usuario utilizando la API de Gemini.
    Extrae la información relevante del gasto en formato JSON estructurado.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "tu_api_key_de_gemini_aqui":
        return {
            "es_gasto": False,
            "monto": 0.0,
            "descripcion": "",
            "categoria": "General",
            "respuesta_chat": "Configura tu GEMINI_API_KEY en el archivo .env para habilitar el procesamiento con IA."
        }
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        Eres un asistente financiero inteligente llamado Cuentita.
        El usuario ha enviado el siguiente mensaje: "{mensaje}".

        Tu tarea es determinar si el mensaje se refiere al registro de un gasto.
        
        Responde ÚNICAMENTE con un objeto JSON sin formato Markdown adicional (sin ```json) con las siguientes claves:
        - "es_gasto": boolean (true si el mensaje indica un gasto, false si es una consulta o saludo general)
        - "monto": float (el valor numérico del gasto, 0.0 si no aplica)
        - "descripcion": string (descripción breve del gasto, p. ej. "Café", "Nafta", "Supermercado")
        - "categoria": string (una de las siguientes: "Comida", "Transporte", "Servicios", "Entretenimiento", "Salud", "Compras", "General")
        - "respuesta_chat": string (una respuesta corta, amable y directa para responder al usuario)
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )

        # Limpiar posible formato markdown que devuelva el modelo
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "", 1)
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "", 1)
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        
        return json.loads(raw_text.strip())

    except Exception as e:
        return {
            "es_gasto": False,
            "monto": 0.0,
            "descripcion": "",
            "categoria": "General",
            "respuesta_chat": f"Hola, tuve un detalle al procesar tu solicitud con la IA: {str(e)}"
        }