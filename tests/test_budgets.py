import unittest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.models.db_models import Gasto, Usuario
from app.routers.auth import router as auth_router
from app.routers.finanzas import router as finanzas_router
from app.security import csrf_protection
from app.services.auth_service import get_current_user


class BudgetApiTests(unittest.TestCase):
    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        with self.session_factory() as db:
            self.owner = Usuario(email="owner@example.com", hashed_password="unused")
            self.other = Usuario(email="other@example.com", hashed_password="unused")
            db.add_all([self.owner, self.other])
            db.commit()
            db.refresh(self.owner)
            db.refresh(self.other)
            self.owner_id = self.owner.id
            self.other_id = self.other.id

        self.owner_client = self.create_client(self.owner_id)
        self.other_client = self.create_client(self.other_id)
        self.owner_client.get("/api/presupuestos")
        self.other_client.get("/api/presupuestos")
        self.owner_csrf = self.csrf_header(self.owner_client)
        self.other_csrf = self.csrf_header(self.other_client)

    def create_client(self, user_id: int) -> TestClient:
        app = FastAPI()
        app.middleware("http")(csrf_protection)
        app.include_router(finanzas_router)
        app.include_router(auth_router)

        def get_test_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        with self.session_factory() as db:
            user = db.query(Usuario).filter(Usuario.id == user_id).first()

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def csrf_header(self, client: TestClient) -> dict[str, str]:
        return {"X-CSRF-Token": client.cookies["csrf_token"]}

    def tearDown(self):
        self.owner_client.close()
        self.other_client.close()
        self.engine.dispose()

    def create_budget(self, client: TestClient, category: str, amount: float):
        return client.post(
            "/api/presupuestos",
            json={"categoria": category, "monto_maximo": amount},
            headers=self.owner_csrf if client is self.owner_client else self.other_csrf,
        )

    def add_expense(self, user_id: int, category: str, amount: float, date: datetime):
        with self.session_factory() as db:
            db.add(Gasto(
                usuario_id=user_id,
                categoria=category,
                monto=amount,
                descripcion=f"Gasto {category}",
                fecha=date,
            ))
            db.commit()

    def test_budgets_are_optional_and_monthly_progress_has_discreet_threshold_states(self):
        self.add_expense(self.owner_id, "Alimentación", 800, self.utcnow())
        self.add_expense(self.owner_id, "Transporte", 250, self.utcnow())
        self.add_expense(self.owner_id, "Entretenimiento", 500, self.utcnow())
        self.add_expense(self.owner_id, "Servicios", 10_000, self.utcnow())

        prior_month = self.utcnow().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ) - timedelta(seconds=1)
        self.add_expense(self.owner_id, "Alimentación", 5000, prior_month)

        self.assertEqual(self.owner_client.get("/api/presupuestos").json(), [])
        food = self.create_budget(self.owner_client, "Alimentación", 1000)
        transport = self.create_budget(self.owner_client, "Transporte", 200)
        entertainment = self.create_budget(self.owner_client, "Entretenimiento", 500)
        unused = self.create_budget(self.owner_client, "Salud", 500)
        self.assertEqual(food.status_code, 201, food.text)
        self.assertEqual(transport.status_code, 201, transport.text)
        self.assertEqual(entertainment.status_code, 201, entertainment.text)
        self.assertEqual(unused.status_code, 201, unused.text)

        response = self.owner_client.get("/api/presupuestos")
        self.assertEqual(response.status_code, 200)
        summaries = {item["categoria"]: item for item in response.json()}
        self.assertEqual(summaries["Alimentación"]["gastado"], 800)
        self.assertEqual(summaries["Alimentación"]["estado"], "cerca")
        self.assertEqual(summaries["Transporte"]["porcentaje"], 125)
        self.assertEqual(summaries["Transporte"]["estado"], "superado")
        self.assertEqual(summaries["Entretenimiento"]["porcentaje"], 100)
        self.assertEqual(summaries["Entretenimiento"]["estado"], "superado")
        self.assertEqual(summaries["Salud"]["gastado"], 0)
        self.assertEqual(summaries["Salud"]["estado"], "normal")

    def test_user_can_update_and_remove_own_budget_but_not_another_users(self):
        budget = self.create_budget(self.owner_client, "Compras", 1000)
        budget_id = budget.json()["id"]
        other_budget = self.create_budget(self.other_client, "Compras", 700)
        self.assertEqual(other_budget.status_code, 201, other_budget.text)
        self.assertEqual(
            [item["monto_maximo"] for item in self.other_client.get("/api/presupuestos").json()],
            [700],
        )
        self.assertEqual(
            [item["monto_maximo"] for item in self.owner_client.get("/api/presupuestos").json()],
            [1000],
        )

        self.assertEqual(self.create_budget(self.owner_client, "Compras", 500).status_code, 409)
        self.assertEqual(
            self.other_client.put(
                f"/api/presupuestos/{budget_id}",
                json={"categoria": "Compras", "monto_maximo": 1},
                headers=self.other_csrf,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.other_client.delete(
                f"/api/presupuestos/{budget_id}",
                headers=self.other_csrf,
            ).status_code,
            404,
        )

        updated = self.owner_client.put(
            f"/api/presupuestos/{budget_id}",
            json={"categoria": "Compras", "monto_maximo": 2000},
            headers=self.owner_csrf,
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["monto_maximo"], 2000)

        deleted = self.owner_client.delete(
            f"/api/presupuestos/{budget_id}",
            headers=self.owner_csrf,
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(self.owner_client.get("/api/presupuestos").json(), [])

    def test_invalid_budget_values_are_rejected(self):
        for data in (
            {"categoria": "   ", "monto_maximo": 100},
            {"categoria": "Salud", "monto_maximo": 0},
            {"categoria": "x" * 51, "monto_maximo": 100},
        ):
            with self.subTest(data=data):
                response = self.owner_client.post(
                    "/api/presupuestos",
                    json=data,
                    headers=self.owner_csrf,
                )
                self.assertEqual(response.status_code, 422)

        self.assertEqual(self.owner_client.get("/api/presupuestos").json(), [])

    def test_dashboard_links_to_a_separate_monthly_planning_page(self):
        dashboard = self.owner_client.get("/dashboard")
        planning = self.owner_client.get("/planificacion")

        self.assertEqual(dashboard.status_code, 200)
        self.assertIn('href="/planificacion"', dashboard.text)
        self.assertNotIn('id="presupuestoForm"', dashboard.text)
        self.assertNotIn('id="gastosFijosPanel"', dashboard.text)
        self.assertIn('/static/js/dashboard.js', dashboard.text)

        self.assertEqual(planning.status_code, 200)
        self.assertIn("Planificación mensual", planning.text)
        self.assertIn('id="presupuestoForm"', planning.text)
        self.assertIn('id="gastosFijosPanel"', planning.text)
        self.assertIn('/static/js/planificacion.js', planning.text)


if __name__ == "__main__":
    unittest.main()
