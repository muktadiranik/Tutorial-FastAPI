import importlib
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import bcrypt
import jwt
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Do not connect to or modify the tutorial's PostgreSQL database.
        with (
            patch.dict(os.environ, {"JWT_SECRET_KEY": "test-signing-key-" * 4}),
            patch("sqlalchemy.sql.schema.MetaData.create_all"),
            patch("psycopg2.connect"),
        ):
            cls.main = importlib.import_module("7.app.main")
            cls.models = importlib.import_module("7.app.models")
            cls.database_module = importlib.import_module("7.app.database")
            cls.auth = importlib.import_module("7.app.utilities")
            cls.bcrypt_auth = importlib.import_module("7.app.authentication")

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.models.Base.metadata.create_all(bind=self.engine)
        self.database = sessionmaker(bind=self.engine)()
        self.main.app.dependency_overrides[self.database_module.get_database] = (
            lambda: self.database
        )
        self.client = TestClient(self.main.app)
        self.user_data = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "a-secure-password",
        }

    def tearDown(self):
        self.client.close()
        self.main.app.dependency_overrides.clear()
        self.database.close()
        self.engine.dispose()

    def register(self):
        response = self.client.post("/users", json=self.user_data)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def encode_token(self, claims, key=None, algorithm="HS256"):
        token = jwt.encode(
            claims, key or self.auth.SECRET_KEY, algorithm=algorithm
        )
        return token.decode("utf-8") if isinstance(token, bytes) else token

    def assert_unauthorized(self, response):
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_registration_hashes_password_and_returns_only_public_fields(self):
        user = self.register()
        self.assertEqual(set(user), {"id", "username", "email"})
        stored = self.database.query(self.models.User).one()
        self.assertNotEqual(stored.password, self.user_data["password"])
        self.assertTrue(stored.password.startswith("$argon2id$"))
        self.assertTrue(self.auth.verify_password(
            self.user_data["password"], stored.password
        ))
        self.assertIsNotNone(stored.created_at)
        self.assertIsNotNone(stored.updated_at)

    def test_duplicate_username_or_email_rolls_back_transaction(self):
        self.register()
        for changes in (
            {"email": "other@example.com"},
            {"username": "bob"},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(
                    "/users", json={**self.user_data, **changes}
                )
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(self.database.query(self.models.User).count(), 1)
        response = self.client.post("/users", json={
            **self.user_data, "username": "bob", "email": "bob@example.com"
        })
        self.assertEqual(response.status_code, 201, response.text)

    def test_commit_integrity_error_rolls_back(self):
        with (
            patch.object(self.database, "commit", side_effect=IntegrityError(
                "INSERT", {}, Exception("unique constraint")
            )),
            patch.object(self.database, "rollback", wraps=self.database.rollback) as rollback,
        ):
            response = self.client.post("/users", json=self.user_data)
            self.assertEqual(response.status_code, 409)
            rollback.assert_called_once()

    def test_registration_validation(self):
        for changes in (
            {"username": ""},
            {"username": "   "},
            {"email": "not-an-email"},
            {"password": "short"},
            {"password": "a" * 73},
            {"password": "é" * 37},
        ):
            with self.subTest(changes=changes):
                response = self.client.post(
                    "/users", json={**self.user_data, **changes}
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.database.query(self.models.User).count(), 0)

    def test_login_and_current_user(self):
        user = self.register()
        response = self.client.post("/login", json={
            "email": self.user_data["email"], "password": self.user_data["password"]
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        token = response.json()
        self.assertEqual(token["token_type"], "bearer")
        self.assertIsInstance(token["access_token"], str)
        claims = jwt.decode(
            token["access_token"], self.auth.SECRET_KEY,
            algorithms=[self.auth.ALGORITHM],
        )
        self.assertEqual(claims["sub"], str(user["id"]))
        remaining = claims["exp"] - datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(remaining, 30 * 60, delta=5)
        response = self.client.get("/users/me", headers={
            "Authorization": f"Bearer {token['access_token']}"
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), user)

    def test_invalid_credentials_share_generic_error(self):
        self.register()
        for email, password in (
            ("alice@example.com", "wrong-password"),
            ("missing-user@example.com", "wrong-password"),
            ("alice@example.com", "a" * 73),
        ):
            with self.subTest(email=email, password=password):
                response = self.client.post("/login", json={
                    "email": email, "password": password
                })
                self.assert_unauthorized(response)
                self.assertEqual(
                    response.json()["detail"], "Incorrect email or password"
                )

    def test_login_rejects_form_data(self):
        self.register()
        response = self.client.post("/login", data={
            "email": self.user_data["email"], "password": self.user_data["password"]
        })
        self.assertEqual(response.status_code, 422, response.text)

    def test_login_validates_json_body(self):
        for payload in (
            {},
            {"email": "alice@example.com"},
            {"password": "a-secure-password"},
            {"email": "invalid-email", "password": "a-secure-password"},
            {"email": "alice@example.com", "password": 123},
            {"username": "alice", "password": "a-secure-password"},
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/login", json=payload)
                self.assertEqual(response.status_code, 422, response.text)
        response = self.client.post(
            "/login", content="{", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_plaintext_legacy_password_does_not_authenticate(self):
        self.register()
        user = self.database.query(self.models.User).one()
        user.password = self.user_data["password"]
        self.database.commit()
        self.assert_unauthorized(self.client.post("/login", json={
            "email": self.user_data["email"], "password": self.user_data["password"]
        }))

    def test_current_user_requires_bearer_token(self):
        self.assert_unauthorized(self.client.get("/users/me"))
        self.assert_unauthorized(self.client.get("/users/me", headers={
            "Authorization": "Basic abc"
        }))
        self.assert_unauthorized(self.client.get("/users/me", headers={
            "Authorization": "Bearer "
        }))

    def test_rejects_invalid_expired_or_incomplete_tokens(self):
        user = self.register()
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        claims = {"sub": str(user["id"]), "exp": future}
        tokens = {
            "malformed": "not-a-jwt",
            "wrong_signature": self.encode_token(claims, key="different-key" * 4),
            "wrong_algorithm": self.encode_token(claims, algorithm="HS512"),
            "expired": self.encode_token({
                **claims, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)
            }),
            "no_expiry": self.encode_token({"sub": str(user["id"])}),
            "no_subject": self.encode_token({"exp": future}),
            "invalid_subject": self.encode_token({**claims, "sub": "not-an-id"}),
            "numeric_subject": self.encode_token({**claims, "sub": user["id"]}),
            "null_expiry": self.encode_token({**claims, "exp": None}),
            "out_of_range_subject": self.encode_token({**claims, "sub": str(2 ** 63)}),
            "nonexistent_user": self.encode_token({**claims, "sub": "999"}),
        }
        for label, token in tokens.items():
            with self.subTest(token=label):
                self.assert_unauthorized(self.client.get("/users/me", headers={
                    "Authorization": f"Bearer {token}"
                }))

    def test_deleted_user_token_is_rejected(self):
        user = self.register()
        token = self.auth.create_access_token({"sub": str(user["id"])})
        self.database.delete(self.database.query(self.models.User).one())
        self.database.commit()
        self.assert_unauthorized(self.client.get("/users/me", headers={
            "Authorization": f"Bearer {token}"
        }))

    def test_existing_bcrypt_password_still_authenticates(self):
        self.register()
        user = self.database.query(self.models.User).one()
        user.password = bcrypt.hashpw(
            self.user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        self.database.commit()
        response = self.client.post("/login", json={
            "email": self.user_data["email"], "password": self.user_data["password"]
        })
        self.assertEqual(response.status_code, 200, response.text)
        profile = self.client.get("/users/me", headers={
            "Authorization": f"Bearer {response.json()['access_token']}"
        })
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["id"], user.id)

    def test_utility_lookup_uses_database_users(self):
        user = self.register()
        self.assertEqual(
            self.auth.get_user(self.database, self.user_data["email"]).id,
            user["id"],
        )
        self.assertIsNone(self.auth.get_user(self.database, "johndoe@example.com"))
        self.assertIsNone(self.auth.authenticate_user(
            self.database, "johndoe@example.com", "secret"
        ))

    def test_utility_token_supports_custom_expiry_without_mutating_input(self):
        data = {"sub": "1"}
        token = self.auth.create_access_token(data, timedelta(minutes=5))
        claims = jwt.decode(token, self.auth.SECRET_KEY, algorithms=[self.auth.ALGORITHM])
        self.assertEqual(data, {"sub": "1"})
        remaining = claims["exp"] - datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(remaining, 5 * 60, delta=5)
        token = self.auth.create_access_token(data, timedelta(0))
        claims = jwt.decode(
            token, self.auth.SECRET_KEY, algorithms=[self.auth.ALGORITHM],
            options={"verify_exp": False},
        )
        self.assertLessEqual(claims["exp"], datetime.now(timezone.utc).timestamp())

    def test_profile_uses_active_user_dependency(self):
        self.register()
        user = self.database.query(self.models.User).one()
        user.disabled = True
        self.main.app.dependency_overrides[self.auth.get_current_user] = lambda: user
        response = self.client.get("/users/me")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"], "Inactive user")

    def test_openapi_describes_json_login_and_bearer_authentication(self):
        schema = self.client.get("/openapi.json").json()
        security = schema["components"]["securitySchemes"]["HTTPBearer"]
        self.assertEqual(security["type"], "http")
        self.assertEqual(security["scheme"], "bearer")
        self.assertIn("201", schema["paths"]["/users"]["post"]["responses"])
        self.assertEqual(set(schema["paths"][
            "/login"
        ]["post"]["requestBody"]["content"]), {"application/json"})
        self.assertEqual(
            set(schema["components"]["schemas"]["LoginRequest"]["required"]),
            {"email", "password"},
        )
        self.assertEqual(schema["paths"]["/users/me"]["get"]["security"], [
            {"HTTPBearer": []}
        ])

    def test_bcrypt_registration_login_and_profile(self):
        response = self.client.post("/auth/users", json=self.user_data)
        self.assertEqual(response.status_code, 201, response.text)
        user = response.json()
        self.assertEqual(set(user), {"id", "username", "email"})
        stored = self.database.query(self.models.User).one()
        self.assertTrue(stored.password.startswith("$2b$"))
        self.assertTrue(self.bcrypt_auth.verify_password(
            self.user_data["password"], stored.password
        ))
        response = self.client.post("/auth/login", json={
            "email": self.user_data["email"], "password": self.user_data["password"]
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        token = response.json()
        self.assertEqual(token["token_type"], "bearer")
        claims = jwt.decode(
            token["access_token"], self.bcrypt_auth.SECRET_KEY,
            algorithms=[self.bcrypt_auth.ALGORITHM],
        )
        self.assertEqual(claims["sub"], str(user["id"]))
        remaining = claims["exp"] - datetime.now(timezone.utc).timestamp()
        self.assertAlmostEqual(remaining, 30 * 60, delta=5)
        for endpoint in ("/auth/users/me", "/users/me"):
            with self.subTest(endpoint=endpoint):
                profile = self.client.get(endpoint, headers={
                    "Authorization": f"Bearer {token['access_token']}"
                })
                self.assertEqual(profile.status_code, 200, profile.text)
                self.assertEqual(profile.json(), user)
        response = self.client.post("/login", json={
            "email": self.user_data["email"], "password": self.user_data["password"]
        })
        self.assertEqual(response.status_code, 200, response.text)

    def test_bcrypt_registration_shares_validation_and_uniqueness(self):
        self.register()
        for changes in ({}, {"email": "other@example.com"}, {"username": "bob"}):
            with self.subTest(changes=changes):
                response = self.client.post(
                    "/auth/users", json={**self.user_data, **changes}
                )
                self.assertEqual(response.status_code, 409, response.text)
        for password in ("short", "a" * 73, "é" * 37):
            response = self.client.post("/auth/users", json={
                **self.user_data, "username": "bob", "email": "bob@example.com",
                "password": password,
            })
            self.assertEqual(response.status_code, 422, response.text)
        response = self.client.post("/auth/users", json={
            **self.user_data, "username": "bob", "email": "bob@example.com"
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.database.query(self.models.User).count(), 2)

    def test_bcrypt_login_rejects_invalid_credentials_and_argon2_hashes(self):
        response = self.client.post("/auth/users", json=self.user_data)
        self.assertEqual(response.status_code, 201, response.text)
        for email, password in (
            (self.user_data["email"], "wrong-password"),
            ("missing@example.com", self.user_data["password"]),
            (self.user_data["email"], "a" * 73),
        ):
            with self.subTest(email=email, password=password):
                response = self.client.post("/auth/login", json={
                    "email": email, "password": password
                })
                self.assert_unauthorized(response)
                self.assertEqual(
                    response.json()["detail"], "Incorrect email or password"
                )
        stored = self.database.query(self.models.User).one()
        stored.password = self.auth.get_password_hash(self.user_data["password"])
        self.database.commit()
        self.assert_unauthorized(self.client.post("/auth/login", json={
            "email": self.user_data["email"], "password": self.user_data["password"]
        }))
        for payload in ({}, {"email": "invalid", "password": "password"}):
            response = self.client.post("/auth/login", json=payload)
            self.assertEqual(response.status_code, 422, response.text)
        response = self.client.post("/auth/login", data={
            "email": self.user_data["email"], "password": self.user_data["password"]
        })
        self.assertEqual(response.status_code, 422, response.text)

    def test_bcrypt_profile_rejects_missing_invalid_and_deleted_user_tokens(self):
        self.assert_unauthorized(self.client.get("/auth/users/me"))
        response = self.client.post("/auth/users", json=self.user_data)
        self.assertEqual(response.status_code, 201, response.text)
        user_id = response.json()["id"]
        for token in (
            "not-a-jwt",
            self.encode_token({
                "sub": str(user_id),
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            }),
            self.encode_token({"sub": str(user_id)}),
            self.encode_token({
                "sub": str(user_id),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            }, key="wrong-signing-key-" * 4),
        ):
            self.assert_unauthorized(self.client.get("/auth/users/me", headers={
                "Authorization": f"Bearer {token}"
            }))
        token = self.bcrypt_auth.create_access_token(user_id)
        self.database.delete(self.database.query(self.models.User).one())
        self.database.commit()
        self.assert_unauthorized(self.client.get("/auth/users/me", headers={
            "Authorization": f"Bearer {token}"
        }))

    def test_openapi_exposes_both_authentication_flows(self):
        schema = self.client.get("/openapi.json").json()
        for registration, login, profile in (
            ("/users", "/login", "/users/me"),
            ("/auth/users", "/auth/login", "/auth/users/me"),
        ):
            with self.subTest(login=login):
                self.assertIn("201", schema["paths"][registration]["post"]["responses"])
                self.assertEqual(set(
                    schema["paths"][login]["post"]["requestBody"]["content"]
                ), {"application/json"})
                self.assertEqual(schema["paths"][profile]["get"]["security"], [
                    {"HTTPBearer": []}
                ])

    def test_endpoints_are_registered_from_router_modules(self):
        expected = {
            ("POST", "/users"): "users",
            ("POST", "/login"): "users",
            ("GET", "/users/me"): "users",
            ("POST", "/auth/users"): "authentication",
            ("POST", "/auth/login"): "authentication",
            ("GET", "/auth/users/me"): "authentication",
            ("GET", "/"): "root",
            ("GET", "/models"): "models",
            ("POST", "/models"): "models",
            ("GET", "/courses"): "courses",
            ("GET", "/courses/{course_id}"): "courses",
            ("POST", "/courses"): "courses",
            ("PUT", "/courses/{course_id}"): "courses",
            ("DELETE", "/courses/{course_id}"): "courses",
        }
        registered = [
            ((method, route.path), route.endpoint.__module__)
            for route in self.main.app.routes
            if isinstance(route, APIRoute)
            for method in route.methods
        ]
        self.assertEqual(len(registered), len(expected))
        self.assertEqual(dict(registered), {
            key: f"7.app.router.{module}" for key, module in expected.items()
        })

    def test_root_and_model_routes_remain_public(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"message": "Hello World"})
        response = self.client.get("/models")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"models": ["alexnet", "resnet", "lenet"]})
        response = self.client.post("/models", json={
            "name": "alexnet", "description": "Tutorial", "provider": "Example",
            "website": "https://example.com",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "message": "Model 'alexnet' created successfully!"
        })
        self.assertEqual(self.client.post("/models", json={}).status_code, 422)

    def test_course_routes_remain_public(self):
        instructor = self.register()
        response = self.client.post("/courses", json={
            "name": "FastAPI", "description": "Tutorial", "price": 10.0,
            "instructor_id": instructor["id"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        course_id = response.json()["id"]
        self.assertEqual(self.client.get("/courses").status_code, 200)
        self.assertEqual(self.client.get(f"/courses/{course_id}").status_code, 200)
        response = self.client.put(f"/courses/{course_id}", json={
            "name": "Updated", "description": "Tutorial", "price": 20.0
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "Updated")
        self.assertEqual(self.client.delete(f"/courses/{course_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/courses/{course_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
