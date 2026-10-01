import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.controllers import finanzas_controller
from app.database.connection import Base, get_db
from app.models.db_models import Inversion, SimboloActivo, Usuario
from app.routers.finanzas import router as finanzas_router
from app.security import csrf_protection
from app.services.auth_service import get_current_user
from app.services.asset_symbol_service import normalize_asset_name, resolve_asset_symbol
from app.services.gemini_service import (
    GeminiAssetSymbolResult,
    GeminiServiceError,
    identificar_simbolo_activo,
)


class AssetSymbolServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_asset_names_are_normalized_across_case_accents_and_punctuation(self):
        self.assertEqual(
            normalize_asset_name("  Fóndo—Común  "),
            normalize_asset_name("fondo comun"),
        )

    def test_ai_result_is_cached_and_reused_without_another_ai_call(self):
        with self.session_factory() as db:
            with patch(
                "app.services.asset_symbol_service.identificar_simbolo_activo",
                return_value=GeminiAssetSymbolResult(simbolo="BTC"),
            ) as identify:
                first = resolve_asset_symbol(db, "  Bitcoin  ")
                second = resolve_asset_symbol(db, "bitcoin")

        self.assertEqual(first.symbol, "BTC")
        self.assertEqual(first.status, "found")
        self.assertEqual(second, first)
        identify.assert_called_once_with("  Bitcoin  ")

    def test_unidentified_asset_is_cached_to_avoid_repeated_token_use(self):
        with self.session_factory() as db:
            with patch(
                "app.services.asset_symbol_service.identificar_simbolo_activo",
                return_value=GeminiAssetSymbolResult(simbolo=None),
            ) as identify:
                first = resolve_asset_symbol(db, "Mi fondo privado")
                second = resolve_asset_symbol(db, "mi fondo privado")
            cached_count = db.query(SimboloActivo).count()

        self.assertEqual(first.status, "not_found")
        self.assertEqual(second, first)
        self.assertEqual(cached_count, 1)
        identify.assert_called_once()

    def test_symbol_on_existing_investment_is_reused_before_calling_gemini(self):
        with self.session_factory() as db:
            db.add(Inversion(
                activo="Bitcoin",
                simbolo="BTC",
                monto=120,
                usuario_id=1,
            ))
            db.commit()

            with patch("app.services.asset_symbol_service.identificar_simbolo_activo") as identify:
                result = resolve_asset_symbol(db, "bitcoin")
            cached = db.query(SimboloActivo).one()

        self.assertEqual(result.symbol, "BTC")
        self.assertEqual(cached.simbolo, "BTC")
        identify.assert_not_called()

    def test_transient_ai_failure_is_not_cached(self):
        with self.session_factory() as db:
            with patch(
                "app.services.asset_symbol_service.identificar_simbolo_activo",
                side_effect=GeminiServiceError("unavailable"),
            ) as identify:
                for _ in range(2):
                    with self.assertRaises(GeminiServiceError):
                        resolve_asset_symbol(db, "Bitcoin")
            cached_count = db.query(SimboloActivo).count()

        self.assertEqual(cached_count, 0)
        self.assertEqual(identify.call_count, 2)

    def test_gemini_symbol_parser_validates_and_normalizes_ticker(self):
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(
            text=json.dumps({"simbolo": "aapl"})
        )

        with (
            patch("app.services.gemini_service.settings.GEMINI_API_KEY", "test-key"),
            patch("app.services.gemini_service.genai.Client", return_value=client),
        ):
            result = identificar_simbolo_activo("Apple")

        self.assertEqual(result.simbolo, "AAPL")
        client.models.generate_content.assert_called_once()
        self.assertEqual(
            client.models.generate_content.call_args.kwargs["config"],
            {"max_output_tokens": 64, "temperature": 0},
        )


class InvestmentCreateEndpointTests(unittest.TestCase):
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
        self.app.include_router(finanzas_router)
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

    def test_create_resolves_symbol_and_uses_live_quote_without_extra_form_fields(self):
        with (
            patch(
                "app.controllers.finanzas_controller.resolve_asset_symbol",
                return_value=finanzas_controller.SymbolResolution("BTC", "found"),
            ),
            patch(
                "app.controllers.finanzas_controller.obtener_cotizacion",
                return_value={
                    "precio_usd": 120,
                    "variacion_24h": 2.5,
                    "proveedor": "test",
                },
            ) as get_quote,
        ):
            response = self.client.post(
                "/api/inversiones",
                json={
                    "activo": "Bitcoin",
                    "cantidad": 0.5,
                    "monto": 50,
                    "monto_invertido": 50,
                    "rendimiento": 8,
                },
                headers=self.csrf_header,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["simbolo"], "BTC")
        self.assertEqual(response.json()["monto_invertido"], 50)
        self.assertEqual(response.json()["precio_actual"], 120)
        self.assertEqual(response.json()["monto"], 60)
        get_quote.assert_called_once_with("BTC")

    def test_create_succeeds_with_purchase_value_when_ai_is_temporarily_unavailable(self):
        with (
            patch(
                "app.controllers.finanzas_controller.resolve_asset_symbol",
                side_effect=GeminiServiceError("unavailable"),
            ),
            patch("app.controllers.finanzas_controller.obtener_cotizacion") as get_quote,
        ):
            response = self.client.post(
                "/api/inversiones",
                json={
                    "activo": "Bitcoin",
                    "cantidad": 2,
                    "monto": 80,
                    "monto_invertido": 80,
                    "rendimiento": 5,
                },
                headers=self.csrf_header,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["simbolo"])
        self.assertEqual(response.json()["monto"], 80)
        self.assertEqual(response.json()["precio_actual"], 40)
        get_quote.assert_not_called()

    def test_create_converts_peso_cost_to_usd_and_preserves_original_amount(self):
        with (
            patch(
                "app.controllers.finanzas_controller.resolve_asset_symbol",
                return_value=finanzas_controller.SymbolResolution("BTC", "found"),
            ),
            patch(
                "app.controllers.finanzas_controller.obtener_cotizacion",
                return_value=None,
            ),
        ):
            response = self.client.post(
                "/api/inversiones",
                json={
                    "activo": "Bitcoin",
                    "cantidad": 2,
                    "moneda_inversion": "ARS",
                    "monto_invertido_original": 150000,
                    "tipo_cambio_ars_usd": 1500,
                    "monto": 100,
                    "monto_invertido": 100,
                    "rendimiento": 8,
                },
                headers=self.csrf_header,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["moneda_inversion"], "ARS")
        self.assertEqual(response.json()["monto_invertido_original"], 150000)
        self.assertEqual(response.json()["tipo_cambio_ars_usd"], 1500)
        self.assertEqual(response.json()["monto_invertido"], 100)
        self.assertEqual(response.json()["precio_actual"], 50)
        self.assertEqual(response.json()["monto"], 100)

    def test_create_rejects_ars_investment_without_manual_exchange_rate(self):
        response = self.client.post(
            "/api/inversiones",
            json={
                "activo": "Bitcoin",
                "cantidad": 2,
                "moneda_inversion": "ARS",
                "monto_invertido_original": 150000,
                "monto": 100,
                "monto_invertido": 100,
                "rendimiento": 8,
            },
            headers=self.csrf_header,
        )

        self.assertEqual(response.status_code, 422)

    def test_update_preserves_usd_valuation_and_recomputes_ars_cost_basis(self):
        with (
            patch(
                "app.controllers.finanzas_controller.resolve_asset_symbol",
                return_value=finanzas_controller.SymbolResolution("BTC", "found"),
            ),
            patch(
                "app.controllers.finanzas_controller.obtener_cotizacion",
                return_value=None,
            ),
        ):
            created = self.client.post(
                "/api/inversiones",
                json={
                    "activo": "Bitcoin",
                    "simbolo": "BTC",
                    "cantidad": 2,
                    "monto": 100,
                    "monto_invertido": 100,
                    "monto_invertido_original": 100,
                    "precio_actual": 50,
                    "rendimiento": 8,
                },
                headers=self.csrf_header,
            )
            investment_id = created.json()["id"]
            updated = self.client.put(
                f"/api/inversiones/{investment_id}",
                json={
                    "activo": "Bitcoin",
                    "simbolo": "BTC",
                    "cantidad": 2,
                    "moneda_inversion": "ARS",
                    "monto_invertido_original": 150000,
                    "tipo_cambio_ars_usd": 1500,
                    "monto": 100,
                    "monto_invertido": 100,
                    "precio_actual": 50,
                    "rendimiento": 8,
                },
                headers=self.csrf_header,
            )

        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["moneda_inversion"], "ARS")
        self.assertEqual(updated.json()["monto_invertido_original"], 150000)
        self.assertEqual(updated.json()["monto_invertido"], 100)
        self.assertEqual(updated.json()["precio_actual"], 50)


if __name__ == "__main__":
    unittest.main()
