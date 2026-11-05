import importlib
import io
import logging
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


logging_config = importlib.import_module("7.app.logging_config")
middleware = importlib.import_module("7.app.middleware")


class LoggingConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("7.app")
        self.previous_state = (
            self.logger.handlers[:], self.logger.level, self.logger.propagate
        )
        self.logger.handlers = []
        self.stream = io.StringIO()
        self.stderr_patch = patch("sys.stderr", self.stream)
        self.stderr_patch.start()
        self.env_file_patch = patch.object(logging_config, "load_dotenv")
        self.env_file_patch.start()

    def tearDown(self):
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers, level, self.logger.propagate = self.previous_state
        self.logger.setLevel(level)
        self.env_file_patch.stop()
        self.stderr_patch.stop()

    def test_default_configuration_logs_info_to_console(self):
        with patch.dict(os.environ):
            os.environ.pop("LOG_LEVEL", None)
            logging_config.configure_logging()
        self.logger.info("Application ready")
        self.logger.debug("Hidden debug message")
        output = self.stream.getvalue()
        self.assertIn(" | INFO | 7.app | Application ready", output)
        self.assertNotIn("Hidden debug message", output)

    def test_level_is_configurable_and_case_insensitive(self):
        with patch.dict(os.environ, {"LOG_LEVEL": " debug "}):
            logging_config.configure_logging()
        self.logger.debug("Session opened")
        self.assertIn("DEBUG", self.stream.getvalue())

    def test_invalid_level_falls_back_to_info(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "invalid"}):
            logging_config.configure_logging()
        self.assertEqual(self.logger.level, logging.INFO)
        self.assertIn("Invalid LOG_LEVEL; using INFO", self.stream.getvalue())

    def test_configuration_is_idempotent_and_leaves_root_logger_alone(self):
        root = logging.getLogger()
        root_state = root.handlers[:], root.level
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
            logging_config.configure_logging()
            logging_config.configure_logging()
        self.logger.info("Only once")
        self.assertEqual(self.stream.getvalue().count("Only once"), 1)
        self.assertEqual((root.handlers, root.level), root_state)

    def test_exception_output_keeps_type_and_location_but_not_message(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
            logging_config.configure_logging()
        secret = "private-password-and-sql-parameters"
        try:
            raise ValueError(secret)
        except ValueError:
            self.logger.exception("Operation failed")
        output = self.stream.getvalue()
        self.assertIn("ValueError", output)
        self.assertIn("test_logging.py", output)
        self.assertNotIn(secret, output)


class RequestLoggingTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.middleware("http")(middleware.log_requests)

        @app.get("/items/{item_id}")
        def get_item(item_id: str):
            return {"item_id": item_id}

        @app.get("/denied")
        def denied():
            raise HTTPException(status_code=401, detail="Not authorized")

        @app.get("/unavailable")
        def unavailable():
            return Response(status_code=503)

        @app.get("/broken")
        def broken():
            raise RuntimeError("private-exception-message")

        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()

    def test_request_logs_template_status_and_duration_without_sensitive_values(self):
        with self.assertLogs(middleware.logger, level="INFO") as captured:
            response = self.client.get(
                "/items/private-path?token=private-query",
                headers={"Authorization": "Bearer private-header"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"item_id": "private-path"})
        self.assertEqual(len(captured.records), 1)
        output = "\n".join(captured.output)
        self.assertIn("method=GET route=/items/{item_id} status=200 duration_ms=", output)
        for secret in ("private-path", "private-query", "private-header"):
            self.assertNotIn(secret, output)

    def test_client_and_server_errors_use_expected_log_levels(self):
        for path, status_code, level in (
            ("/denied", 401, logging.WARNING),
            ("/unavailable", 503, logging.ERROR),
        ):
            with self.subTest(path=path):
                with self.assertLogs(middleware.logger) as captured:
                    response = self.client.get(path)
                self.assertEqual(response.status_code, status_code)
                self.assertEqual(captured.records[0].levelno, level)
                self.assertIn(f"status={status_code}", captured.output[0])

    def test_unknown_path_is_not_logged(self):
        with self.assertLogs(middleware.logger) as captured:
            response = self.client.get("/private-unknown-url?password=private-query")
        self.assertEqual(response.status_code, 404)
        self.assertIn("route=<unmatched>", captured.output[0])
        self.assertNotIn("private-", captured.output[0])

    def test_unhandled_exception_is_logged_without_changing_error_behavior(self):
        with self.assertLogs(middleware.logger) as captured:
            response = self.client.get("/broken")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertIsNotNone(record.exc_info)
        self.assertIn("Request failed", record.getMessage())
        # Even a cached rendering from another handler must be sanitized.
        output = logging_config.SafeExceptionFormatter().format(record)
        self.assertIn("RuntimeError", output)
        self.assertNotIn("private-exception-message", output)


class ApplicationLoggingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Exercise real routers, without touching the tutorial's PostgreSQL DB.
        with (
            patch.dict(os.environ, {"JWT_SECRET_KEY": "test-signing-key-" * 4}),
            patch("sqlalchemy.sql.schema.MetaData.create_all"),
            patch("psycopg2.connect"),
        ):
            cls.main = importlib.import_module("7.app.main")
            cls.models = importlib.import_module("7.app.models")
            cls.database_module = importlib.import_module("7.app.database")

    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.models.Base.metadata.create_all(bind=self.engine)
        self.database = sessionmaker(bind=self.engine)()
        self.main.app.dependency_overrides[self.database_module.get_database] = (
            lambda: self.database
        )
        self.client = TestClient(self.main.app)

    def tearDown(self):
        self.client.close()
        self.main.app.dependency_overrides.clear()
        self.database.close()
        self.engine.dispose()

    def test_both_authentication_routers_log_outcomes_without_credentials(self):
        for registration, login, label in (
            ("/users/", "/users/login", "pwdlib"),
            ("/auth/users", "/auth/login", "bcrypt"),
        ):
            with self.subTest(router=label):
                user = {
                    "username": f"private-user-{label}",
                    "email": f"private-{label}@example.com",
                    "password": "private-test-password",
                }
                with self.assertLogs("7.app", level="DEBUG") as captured:
                    self.assertEqual(self.client.post(registration, json=user).status_code, 201)
                    self.assertEqual(self.client.post(registration, json=user).status_code, 409)
                    rejected = self.client.post(login, json={
                        "email": user["email"], "password": "private-wrong-password",
                    })
                    self.assertEqual(rejected.status_code, 401)
                    accepted = self.client.post(login, json={
                        "email": user["email"], "password": user["password"],
                    })
                    self.assertEqual(accepted.status_code, 200)
                output = "\n".join(captured.output)
                for message in ("User registered", "Registration rejected", "Login rejected", "Login successful"):
                    self.assertIn(message, output)
                for secret in (*user.values(), "private-wrong-password", accepted.json()["access_token"]):
                    self.assertNotIn(secret, output)

    def test_course_changes_are_logged(self):
        instructor = self.models.User(
            username="instructor", email="instructor@example.com", password="test-hash"
        )
        self.database.add(instructor)
        self.database.commit()
        course = {
            "name": "FastAPI", "description": "Tutorial", "price": 10.0,
            "instructor_id": instructor.id,
        }
        with self.assertLogs("7.app", level="DEBUG") as captured:
            created = self.client.post("/courses/", json=course)
            self.assertEqual(created.status_code, 200)
            course_id = created.json()["id"]
            self.assertEqual(self.client.put(f"/courses/{course_id}", json=course).status_code, 200)
            self.assertEqual(self.client.delete(f"/courses/{course_id}").status_code, 200)
            self.assertEqual(self.client.get(f"/courses/{course_id}").status_code, 404)
        output = "\n".join(captured.output)
        for message in ("Course created", "Course updated", "Course deleted", "Course not found"):
            self.assertIn(f"{message} course_id={course_id}", output)

    def test_database_session_lifecycle_is_logged_at_debug_level(self):
        with (
            patch.object(self.database_module, "SessionLocal", return_value=self.database),
            self.assertLogs("7.app", level="DEBUG") as captured,
        ):
            dependency = self.database_module.get_database()
            self.assertIs(next(dependency), self.database)
            dependency.close()
        self.assertIn("Database session opened", captured.output[0])
        self.assertIn("Database session closed", captured.output[1])


if __name__ == "__main__":
    unittest.main()
