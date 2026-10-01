import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.models.db_models import Gasto, Usuario
from app.routers.chat import router as chat_router
from app.security import csrf_protection
from app.services.auth_service import get_current_user
from app.services.gemini_service import (
    GeminiExpenseResult,
    GeminiServiceError,
    procesar_mensaje_gasto,
)


class GeminiServiceTests(unittest.TestCase):
    def test_parses_valid_json_response_with_markdown_fence(self):
        model_result = {
            "es_gasto": True,
            "monto": 1800,
            "descripcion": " Nafta ",
            "categoria": "Transporte",
            "respuesta_chat": " Gasto identificado. ",
        }
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=f"```json\n{json.dumps(model_result)}\n```"
        )

        with (
            patch("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key"),
            patch("app.services.gemini_service.genai.Client", return_value=client),
        ):
            resultado = procesar_mensaje_gasto("Pagué nafta")

        self.assertEqual(resultado, GeminiExpenseResult(
            es_gasto=True,
            monto=1800,
            descripcion="Nafta",
            categoria="Transporte",
            respuesta_chat="Gasto identificado.",
        ))

    def test_missing_api_key_raises_service_error(self):
        with (
            patch("app.services.gemini_service.settings.GEMINI_API_KEY", ""),
            patch("app.services.gemini_service.genai.Client") as gemini_client,
        ):
            with self.assertRaises(GeminiServiceError):
                procesar_mensaje_gasto("Pagué nafta")

        gemini_client.assert_not_called()

    def test_malformed_or_invalid_model_responses_raise_service_error(self):
        responses = [
            "not json",
            json.dumps({
                "es_gasto": True,
                "monto": 0,
                "descripcion": "",
                "categoria": "Transporte",
                "respuesta_chat": "No válido",
            }),
            json.dumps({
                "es_gasto": True,
                "monto": 200,
                "descripcion": "Almuerzo",
                "categoria": "Categoría inventada",
                "respuesta_chat": "Registrado",
            }),
            None,
        ]
        with patch("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key"):
            for text in responses:
                with self.subTest(response=text):
                    client = Mock()
                    client.models.generate_content.return_value = SimpleNamespace(text=text)
                    with (
                        patch("app.services.gemini_service.genai.Client", return_value=client),
                        self.assertRaises(GeminiServiceError),
                    ):
                        procesar_mensaje_gasto("Pagué nafta")

    def test_provider_errors_raise_service_error(self):
        with (
            patch("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key"),
            patch(
                "app.services.gemini_service.genai.Client",
                side_effect=RuntimeError("private provider detail"),
            ),
            self.assertRaises(GeminiServiceError),
        ):
            procesar_mensaje_gasto("Pagué nafta")


class ChatEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        test_session = sessionmaker(bind=self.engine)

        def get_test_db():
            db = test_session()
            try:
                yield db
            finally:
                db.close()

        self.app = FastAPI()
        self.app.middleware("http")(csrf_protection)
        self.app.include_router(chat_router)
        self.app.dependency_overrides[get_db] = get_test_db
        self.app.dependency_overrides[get_current_user] = lambda: Usuario(
            id=1,
            email="user@example.com",
            hashed_password="unused",
        )
        self.client = TestClient(self.app)
        self.client.get("/openapi.json")
        self.csrf_header = {"X-CSRF-Token": self.client.cookies["csrf_token"]}

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def gasto_count(self) -> int:
        with sessionmaker(bind=self.engine)() as db:
            return db.query(Gasto).count()

    def test_non_expense_is_returned_without_persisting_a_zero_amount_record(self):
        resultado = GeminiExpenseResult(
            es_gasto=False,
            monto=0,
            descripcion="",
            categoria="General",
            respuesta_chat="Puedo ayudarte a registrar un gasto.",
        )
        with patch("app.controllers.chat_controller.procesar_mensaje_gasto", return_value=resultado):
            response = self.client.post(
                "/chat/procesar",
                json={"mensaje": "¿Qué puedes hacer?"},
                headers=self.csrf_header,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "es_gasto": False,
            "respuesta_chat": "Puedo ayudarte a registrar un gasto.",
            "gasto": None,
        })
        self.assertEqual(self.gasto_count(), 0)

    def test_valid_expense_is_persisted_and_returned(self):
        resultado = GeminiExpenseResult(
            es_gasto=True,
            monto=1800,
            descripcion="Nafta",
            categoria="Transporte",
            respuesta_chat="Gasto identificado.",
        )
        with patch("app.controllers.chat_controller.procesar_mensaje_gasto", return_value=resultado):
            response = self.client.post(
                "/chat/procesar",
                json={"mensaje": "Pagué nafta por 1800"},
                headers=self.csrf_header,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["es_gasto"])
        self.assertEqual(response.json()["gasto"]["descripcion"], "Nafta")
        self.assertEqual(response.json()["gasto"]["monto"], 1800)
        self.assertEqual(self.gasto_count(), 1)

    def test_ai_failure_is_reported_as_service_unavailable_without_saving(self):
        with patch(
            "app.controllers.chat_controller.procesar_mensaje_gasto",
            side_effect=GeminiServiceError("No se pudo procesar el mensaje con IA. Inténtalo nuevamente."),
        ):
            response = self.client.post(
                "/chat/procesar",
                json={"mensaje": "Pagué nafta"},
                headers=self.csrf_header,
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.gasto_count(), 0)

    def test_blank_and_oversized_messages_are_rejected(self):
        blank = self.client.post(
            "/chat/procesar",
            json={"mensaje": "   "},
            headers=self.csrf_header,
        )
        oversized = self.client.post(
            "/chat/procesar",
            json={"mensaje": "x" * 2001},
            headers=self.csrf_header,
        )

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(oversized.status_code, 422)
        self.assertEqual(self.gasto_count(), 0)


if __name__ == "__main__":
    unittest.main()
