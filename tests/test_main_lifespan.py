import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.database.connection import Base
from app.models.db_models import Categoria


class TrackingSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.was_closed = False

    def close(self):
        super().close()
        self.was_closed = True


class ApplicationLifespanTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.sessions = []
        test_session = sessionmaker(bind=self.engine, class_=TrackingSession)

        def create_test_session():
            db = test_session()
            self.sessions.append(db)
            return db

        self.session_local_patch = patch("main.SessionLocal", create_test_session)
        self.session_local_patch.start()

    def tearDown(self):
        self.session_local_patch.stop()
        self.engine.dispose()

    def test_startup_seeds_default_categories_once_and_closes_session(self):
        with tempfile.TemporaryDirectory() as working_directory:
            original_directory = os.getcwd()
            os.chdir(working_directory)
            try:
                with TestClient(main.app):
                    self.assertEqual(len(self.sessions), 1)
                    self.assertTrue(self.sessions[0].was_closed)
                    static_route = next(route for route in main.app.routes if route.name == "static")
                    self.assertEqual(Path(static_route.app.directory), main.STATIC_DIRECTORY)

                with TestClient(main.app):
                    self.assertEqual(len(self.sessions), 2)
                    self.assertTrue(self.sessions[1].was_closed)
                    with sessionmaker(bind=self.engine)() as db:
                        self.assertEqual(
                            {categoria.nombre for categoria in db.query(Categoria).all()},
                            {
                                "Alimentación",
                                "Transporte",
                                "Servicios",
                                "Entretenimiento",
                                "Salud",
                                "Otros",
                            },
                        )
            finally:
                os.chdir(original_directory)


if __name__ == "__main__":
    unittest.main()
