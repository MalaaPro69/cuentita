import re
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.routers.auth import router as auth_router
from app.routers.gastos import router as gastos_router
from app.security import csrf_protection


class ExpenseIsolationTests(unittest.TestCase):
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

        app = FastAPI()
        app.middleware("http")(csrf_protection)
        app.include_router(auth_router)
        app.include_router(gastos_router)
        app.dependency_overrides[get_db] = get_test_db
        self.owner = TestClient(app)
        self.other_user = TestClient(app)

    def tearDown(self):
        self.owner.close()
        self.other_user.close()
        self.engine.dispose()

    def register_and_login(self, client: TestClient, email: str) -> None:
        client.get("/login")
        csrf_header = {"X-CSRF-Token": client.cookies["csrf_token"]}
        with patch("app.controllers.auth_controller.send_account_email") as send_email:
            registered = client.post(
                "/registro",
                data={"email": email, "password": "a-strong-passphrase"},
                headers=csrf_header,
            )
        self.assertEqual(registered.status_code, 200, registered.text)

        verification_token = re.search(
            r"#token=([A-Za-z0-9_-]+)",
            send_email.call_args.args[2],
        ).group(1)
        verified = client.post(
            "/confirmar-email",
            data={"token": verification_token},
            headers=csrf_header,
        )
        self.assertEqual(verified.status_code, 200, verified.text)

        login = client.post(
            "/login",
            data={"username": email, "password": "a-strong-passphrase"},
            headers=csrf_header,
        )
        self.assertEqual(login.status_code, 200, login.text)

    @staticmethod
    def csrf_header(client: TestClient) -> dict[str, str]:
        return {"X-CSRF-Token": client.cookies["csrf_token"]}

    def test_expenses_and_recurring_expenses_are_isolated_by_user(self):
        self.register_and_login(self.owner, "owner@example.com")
        self.register_and_login(self.other_user, "other@example.com")
        owner_csrf = self.csrf_header(self.owner)
        other_csrf = self.csrf_header(self.other_user)

        owner_expense = self.owner.post(
            "/gastos",
            json={"monto": 1250, "descripcion": "Compra propia", "categoria": "Comida"},
            headers=owner_csrf,
        )
        other_expense = self.other_user.post(
            "/gastos",
            json={"monto": 750, "descripcion": "Compra ajena", "categoria": "Salud"},
            headers=other_csrf,
        )
        self.assertEqual(owner_expense.status_code, 200, owner_expense.text)
        self.assertEqual(other_expense.status_code, 200, other_expense.text)
        owner_expense_id = owner_expense.json()["id"]

        owner_expenses = self.owner.get("/gastos").json()
        other_expenses = self.other_user.get("/gastos").json()
        self.assertEqual([item["descripcion"] for item in owner_expenses], ["Compra propia"])
        self.assertEqual([item["descripcion"] for item in other_expenses], ["Compra ajena"])
        self.assertEqual(
            self.owner.get("/gastos/resumen").json(),
            [{"categoria": "Comida", "total": 1250.0, "cantidad": 1}],
        )
        self.assertEqual(
            self.other_user.get("/gastos/resumen").json(),
            [{"categoria": "Salud", "total": 750.0, "cantidad": 1}],
        )

        self.assertEqual(
            self.other_user.delete(f"/gastos/{owner_expense_id}", headers=other_csrf).status_code,
            404,
        )
        self.assertEqual(
            [item["id"] for item in self.owner.get("/gastos").json()],
            [owner_expense_id],
        )

        owner_fixed = self.owner.post(
            "/gastos/fijos",
            json={
                "descripcion": "Alquiler propio",
                "categoria": "Servicios",
                "monto": 30000,
                "dia_mes": 31,
            },
            headers=owner_csrf,
        )
        other_fixed = self.other_user.post(
            "/gastos/fijos",
            json={
                "descripcion": "Alquiler ajeno",
                "categoria": "Servicios",
                "monto": 25000,
                "dia_mes": 15,
            },
            headers=other_csrf,
        )
        self.assertEqual(owner_fixed.status_code, 200, owner_fixed.text)
        self.assertEqual(other_fixed.status_code, 200, other_fixed.text)
        owner_fixed_id = owner_fixed.json()["id"]

        self.assertEqual(
            self.other_user.put(
                f"/gastos/fijos/{owner_fixed_id}",
                json={
                    "descripcion": "Modificado por otra persona",
                    "categoria": "Servicios",
                    "monto": 1,
                    "dia_mes": 1,
                },
                headers=other_csrf,
            ).status_code,
            404,
        )
        self.assertEqual(
            self.other_user.delete(f"/gastos/fijos/{owner_fixed_id}", headers=other_csrf).status_code,
            404,
        )
        self.assertEqual(
            [item["descripcion"] for item in self.owner.get("/gastos/fijos").json()],
            ["Alquiler propio"],
        )
        self.assertEqual(
            [item["descripcion"] for item in self.other_user.get("/gastos/fijos").json()],
            ["Alquiler ajeno"],
        )

        updated_fixed = self.owner.put(
            f"/gastos/fijos/{owner_fixed_id}",
            json={
                "descripcion": "Alquiler actualizado",
                "categoria": "Servicios",
                "monto": 32000,
                "dia_mes": 31,
            },
            headers=owner_csrf,
        )
        self.assertEqual(updated_fixed.status_code, 200, updated_fixed.text)

        for _ in range(2):
            owner_expenses = self.owner.get("/gastos").json()
            other_expenses = self.other_user.get("/gastos").json()
        self.assertCountEqual(
            [item["descripcion"] for item in owner_expenses],
            ["Compra propia", "Alquiler actualizado"],
        )
        self.assertCountEqual(
            [item["descripcion"] for item in other_expenses],
            ["Compra ajena", "Alquiler ajeno"],
        )
        self.assertEqual(len(owner_expenses), 2)
        self.assertEqual(len(other_expenses), 2)


if __name__ == "__main__":
    unittest.main()
