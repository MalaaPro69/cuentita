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
from app.controllers.auth_controller import get_client_ip
from starlette.requests import Request


class CookieAuthenticationTests(unittest.TestCase):
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
        self.app.include_router(auth_router)
        self.app.include_router(gastos_router)
        self.app.dependency_overrides[get_db] = get_test_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def register_and_login(self):
        self.client.get("/login")
        csrf_header = {"X-CSRF-Token": self.client.cookies["csrf_token"]}
        with patch("app.controllers.auth_controller.send_account_email") as send_email:
            registered = self.client.post(
                "/registro",
                data={"email": "User@Example.com", "password": "a-strong-passphrase"},
                headers=csrf_header,
            )
        self.assertEqual(registered.status_code, 200, registered.text)
        verification_token = re.search(r"#token=([A-Za-z0-9_-]+)", send_email.call_args.args[2]).group(1)
        verified = self.client.post(
            "/confirmar-email",
            data={"token": verification_token},
            headers=csrf_header,
        )
        self.assertEqual(verified.status_code, 200, verified.text)
        return self.client.post(
            "/login",
            data={"username": " USER@example.com ", "password": "a-strong-passphrase"},
            headers=csrf_header,
        )

    def test_login_uses_http_only_cookie_for_protected_api(self):
        response = self.register_and_login()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("access_token", response.json())
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertEqual(self.client.get("/gastos").status_code, 200)
        self.assertEqual(self.client.post("/gastos", json={}).status_code, 403)

    def test_protected_api_rejects_anonymous_and_logged_out_clients(self):
        self.assertEqual(self.client.get("/gastos").status_code, 401)

    def test_new_account_requires_verified_valid_email(self):
        self.client.get("/login")
        csrf_header = {"X-CSRF-Token": self.client.cookies["csrf_token"]}
        invalid_email = self.client.post(
            "/registro",
            data={"email": "not-an-email", "password": "a-strong-passphrase"},
            headers=csrf_header,
        )
        self.assertEqual(invalid_email.status_code, 422)

        with patch("app.controllers.auth_controller.send_account_email") as send_email:
            registered = self.client.post(
                "/registro",
                data={"email": "verified@example.com", "password": "a-strong-passphrase"},
                headers=csrf_header,
            )
        self.assertEqual(registered.status_code, 200, registered.text)
        login_data = {"username": "verified@example.com", "password": "a-strong-passphrase"}
        self.assertEqual(self.client.post("/login", data=login_data, headers=csrf_header).status_code, 403)
        token = re.search(r"#token=([A-Za-z0-9_-]+)", send_email.call_args.args[2]).group(1)
        verification_data = {"token": token}
        self.assertEqual(self.client.post("/confirmar-email", data=verification_data, headers=csrf_header).status_code, 200)
        self.assertEqual(self.client.post("/confirmar-email", data=verification_data, headers=csrf_header).status_code, 400)
        self.assertEqual(self.client.post("/login", data=login_data, headers=csrf_header).status_code, 200)
        self.client.get("/login")
        self.assertEqual(
            self.client.post("/registro", data={"email": "x@example.com", "password": "a-strong-passphrase"}).status_code,
            403,
        )
        self.assertEqual(self.register_and_login().status_code, 200)

        self.assertEqual(self.client.post("/logout", headers={"X-CSRF-Token": self.client.cookies["csrf_token"]}).status_code, 200)
        self.assertEqual(self.client.get("/gastos").status_code, 401)

    def test_login_limits_repeated_failures(self):
        self.client.get("/login")
        csrf_header = {"X-CSRF-Token": self.client.cookies["csrf_token"]}
        for _ in range(5):
            response = self.client.post(
                "/login",
                data={"username": "victim@example.com", "password": "wrong-password"},
                headers=csrf_header,
            )
            self.assertEqual(response.status_code, 401)

        blocked = self.client.post(
            "/login",
            data={"username": "victim@example.com", "password": "wrong-password"},
            headers=csrf_header,
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.headers["retry-after"], "900")

    def test_forwarded_ip_is_used_only_from_trusted_proxy(self):
        untrusted = Request({
            "type": "http",
            "method": "POST",
            "headers": [(b"x-forwarded-for", b"203.0.113.25")],
            "client": ("198.51.100.10", 1234),
        })
        trusted = Request({
            "type": "http",
            "method": "POST",
            "headers": [(b"x-forwarded-for", b"203.0.113.25")],
            "client": ("127.0.0.1", 1234),
        })

        self.assertEqual(get_client_ip(untrusted), "198.51.100.10")
        self.assertEqual(get_client_ip(trusted), "203.0.113.25")

    def test_password_reset_is_one_time_and_invalidates_old_session(self):
        self.assertEqual(self.register_and_login().status_code, 200)
        csrf_header = {"X-CSRF-Token": self.client.cookies["csrf_token"]}
        unknown = self.client.post(
            "/solicitar-recuperacion",
            data={"email": "missing@example.com"},
            headers=csrf_header,
        )
        with patch("app.controllers.auth_controller.send_account_email") as send_email:
            requested = self.client.post(
                "/solicitar-recuperacion",
                data={"email": "user@example.com"},
                headers=csrf_header,
            )
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(unknown.json(), requested.json())
        reset_token = re.search(r"#token=([A-Za-z0-9_-]+)", send_email.call_args.args[2]).group(1)
        reset_data = {"token": reset_token, "password": "a-different-passphrase"}
        self.assertEqual(self.client.post("/restablecer", data=reset_data, headers=csrf_header).status_code, 200)
        self.assertEqual(self.client.post("/restablecer", data=reset_data, headers=csrf_header).status_code, 400)
        self.assertEqual(self.client.get("/gastos").status_code, 401)
        self.assertEqual(
            self.client.post("/login", data={"username": "user@example.com", "password": "a-strong-passphrase"}, headers=csrf_header).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/login", data={"username": "user@example.com", "password": "a-different-passphrase"}, headers=csrf_header).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()