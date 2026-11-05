import importlib
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class UsersWithCoursesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-signing-key-" * 4}):
            cls.router = importlib.import_module("7.app.router.users")
            cls.models = importlib.import_module("7.app.models")
            cls.database_module = importlib.import_module("7.app.database")

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(self.engine.dispose)
        self.models.Base.metadata.create_all(self.engine)
        self.database = sessionmaker(bind=self.engine)()
        self.addCleanup(self.database.close)

        self.app = FastAPI()
        self.app.include_router(self.router.router)
        self.app.dependency_overrides[self.database_module.get_database] = (
            lambda: self.database
        )
        self.current_user = self.models.User(
            id=999,
            username="requester",
            email="requester@example.com",
            password="private-password-hash",
        )
        self.app.dependency_overrides[
            self.router.utilities.get_current_active_user
        ] = lambda: self.current_user
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def add_user(self, username: str, courses: list | None = None):
        user = self.models.User(
            username=username,
            email=f"{username}@example.com",
            password="private-password-hash",
            courses=courses or [],
        )
        self.database.add(user)
        self.database.commit()
        return user

    def test_returns_empty_list_when_no_users_exist(self):
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    def test_paginates_users_without_truncating_their_courses(self):
        expected_ids = []
        for index in range(5):
            user = self.add_user(f"instructor{index}", [
                self.models.Course(name=f"Course {number}") for number in range(3)
            ])
            expected_ids.append(user.id)
        self.database.expunge_all()

        for skip, expected in ((0, expected_ids[:2]), (2, expected_ids[2:4]), (4, expected_ids[4:])):
            with self.subTest(skip=skip):
                response = self.client.get("/users/", params={"skip": skip, "limit": 2})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([user["id"] for user in response.json()], expected)
                for user in response.json():
                    self.assertEqual(len(user["courses"]), 3)
                    self.assertTrue(all(course["instructor_id"] == user["id"] for course in user["courses"]))

    def test_defaults_to_twenty_users_and_accepts_the_maximum_limit(self):
        users = [self.models.User(
            id=3 * (index + 1), username=f"instructor{index}",
            email=f"instructor{index}@example.com", password="test-hash",
        ) for index in range(25)]
        self.database.add_all(users)
        self.database.commit()
        expected_ids = sorted(user.id for user in users)

        for params, expected in (({}, expected_ids[:20]), ({"skip": 20}, expected_ids[20:]),
                                 ({"limit": 100}, expected_ids)):
            with self.subTest(params=params):
                response = self.client.get("/users/", params=params)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([user["id"] for user in response.json()], expected)

    def test_pagination_beyond_the_last_user_returns_an_empty_list(self):
        self.add_user("alice")
        for skip in (1, 999):
            with self.subTest(skip=skip):
                response = self.client.get("/users/", params={"skip": skip})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), [])

    def test_rejects_invalid_user_pagination_parameters(self):
        for params in ({"skip": -1}, {"limit": 0}, {"limit": -1}, {"limit": 101},
                       {"skip": "invalid"}, {"limit": "invalid"}):
            with self.subTest(params=params):
                response = self.client.get("/users/", params=params)
                self.assertEqual(response.status_code, 422, response.text)

    def test_omitted_or_empty_search_returns_an_unfiltered_page(self):
        self.add_user("alice")
        bob = self.add_user("bob")
        for search_params in ({}, {"search": ""}):
            with self.subTest(search_params=search_params):
                response = self.client.get(
                    "/users/", params={"skip": 1, "limit": 1, **search_params}
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([user["id"] for user in response.json()], [bob.id])

    def test_search_matches_username_or_email_before_pagination(self):
        self.add_user("unrelated")
        alice = self.add_user("alice", [self.models.Course(name="FastAPI")])
        alice.email = "teacher@example.com"
        bob = self.add_user("bob")
        bob.email = "alice.contact@example.com"
        self.database.commit()

        response = self.client.get("/users/", params={"search": "alice"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([user["id"] for user in response.json()], [alice.id, bob.id])
        self.assertEqual(len(response.json()[0]["courses"]), 1)

        response = self.client.get("/users/", params={"search": "alice", "skip": 1, "limit": 1})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([user["id"] for user in response.json()], [bob.id])

    def test_search_without_matches_returns_an_empty_list(self):
        self.add_user("alice")
        response = self.client.get("/users/", params={"search": "no-match"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    def test_returns_all_users_with_only_their_own_courses(self):
        alice = self.add_user("alice", [
            self.models.Course(name="FastAPI", description="Tutorial", price=10.0),
            self.models.Course(name="SQLAlchemy", description="ORM", price=20.0),
        ])
        bob = self.add_user("bob", [
            self.models.Course(name="Python", description="Basics", price=5.0),
        ])
        charlie = self.add_user("charlie")
        expected_ids = [alice.id, bob.id, charlie.id]
        self.database.expunge_all()

        response = self.client.get("/users/")

        self.assertEqual(response.status_code, 200, response.text)
        users = response.json()
        self.assertEqual([user["id"] for user in users], expected_ids)
        self.assertEqual(
            {user["username"]: {course["name"] for course in user["courses"]}
             for user in users},
            {"alice": {"FastAPI", "SQLAlchemy"}, "bob": {"Python"}, "charlie": set()},
        )
        for user in users:
            self.assertEqual(set(user), {"id", "username", "email", "courses"})
            for course in user["courses"]:
                self.assertEqual(
                    set(course), {"id", "name", "description", "price", "instructor_id"}
                )
                self.assertEqual(course["instructor_id"], user["id"])
        self.assertNotIn("private-password-hash", response.text)

    def test_accepts_nullable_course_fields(self):
        self.add_user("alice", [self.models.Course(name="FastAPI")])

        response = self.client.get("/users/")

        self.assertEqual(response.status_code, 200, response.text)
        course = response.json()[0]["courses"][0]
        self.assertIsNone(course["description"])
        self.assertIsNone(course["price"])

    def test_loads_courses_in_a_batch(self):
        for index in range(5):
            self.add_user(f"instructor{index}", [self.models.Course(name="FastAPI")])
        self.database.expunge_all()
        statements = []

        def capture_statement(connection, cursor, statement, parameters, context, many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", capture_statement)
        try:
            response = self.client.get("/users/", params={"skip": 1, "limit": 2})
        finally:
            event.remove(self.engine, "before_cursor_execute", capture_statement)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(len(statements), 2)

    def test_requires_bearer_authentication(self):
        self.app.dependency_overrides.pop(self.router.utilities.get_current_active_user)
        for headers in ({}, {"Authorization": "Bearer invalid-token"}):
            with self.subTest(headers=headers):
                response = self.client.get("/users/", headers=headers)
                self.assertEqual(response.status_code, 401, response.text)
                self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_accepts_a_valid_bearer_token(self):
        user = self.add_user("alice", [self.models.Course(name="FastAPI")])
        token = self.router.utilities.create_access_token({"sub": str(user.id)})
        self.app.dependency_overrides.pop(self.router.utilities.get_current_active_user)

        response = self.client.get(
            "/users/", headers={"Authorization": f"Bearer {token}"}
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["username"], "alice")

    def test_current_user_response_is_unchanged(self):
        response = self.client.get("/users/me")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()), {"id", "username", "email"})

    def test_openapi_documents_nested_response_and_authentication(self):
        schema = self.client.get("/openapi.json").json()
        operation = schema["paths"]["/users/"]["get"]
        response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

        self.assertEqual(response_schema["type"], "array")
        self.assertEqual(
            response_schema["items"]["$ref"],
            "#/components/schemas/UserWithCoursesResponseBulk",
        )
        self.assertEqual(operation["security"], [{"HTTPBearer": []}])
        user_schema = schema["components"]["schemas"]["UserWithCoursesResponseBulk"]
        self.assertEqual(
            user_schema["properties"]["courses"]["items"]["$ref"],
            "#/components/schemas/CourseResponseBulk",
        )
        self.assertNotIn("password", user_schema["properties"])

    def test_openapi_documents_user_pagination(self):
        schema = self.client.get("/openapi.json").json()
        parameters = {parameter["name"]: parameter["schema"]
                      for parameter in schema["paths"]["/users/"]["get"]["parameters"]}
        self.assertEqual(parameters["skip"]["default"], 0)
        self.assertEqual(parameters["skip"]["minimum"], 0)
        self.assertEqual(parameters["limit"]["default"], 20)
        self.assertEqual(parameters["limit"]["minimum"], 1)
        self.assertEqual(parameters["limit"]["maximum"], 100)
