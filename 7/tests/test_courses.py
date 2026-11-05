import importlib
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class CourseCreationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = importlib.import_module("7.app.router.courses")
        cls.models = importlib.import_module("7.app.models")
        cls.database_module = importlib.import_module("7.app.database")

    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.addCleanup(self.engine.dispose)
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self.models.Base.metadata.create_all(self.engine)
        self.database = sessionmaker(bind=self.engine)()
        self.addCleanup(self.database.close)
        self.instructor = self.models.User(
            username="instructor", email="instructor@example.com", password="test-hash"
        )
        self.database.add(self.instructor)
        self.database.commit()
        self.payload = {
            "name": "FastAPI", "description": "Tutorial", "price": 10.0,
            "instructor_id": self.instructor.id,
        }
        app = FastAPI()
        app.include_router(self.router.router)
        app.dependency_overrides[self.database_module.get_database] = lambda: self.database
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_creation_saves_the_instructor(self):
        response = self.client.post("/courses/", json=self.payload)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["instructor_id"], self.instructor.id)
        stored = self.database.get(self.models.Course, response.json()["id"])
        self.assertIs(stored.instructor, self.instructor)
        self.assertIn(stored, self.instructor.courses)

    def test_course_detail_includes_a_safe_instructor_object(self):
        created = self.client.post("/courses/", json=self.payload).json()
        expected_instructor = {
            "id": self.instructor.id,
            "username": self.instructor.username,
            "email": self.instructor.email,
        }
        self.database.expunge_all()

        response = self.client.get(f"/courses/{created['id']}")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {**created, "instructor": expected_instructor})
        self.assertNotIn("password", response.text)
        self.assertNotIn("test-hash", response.text)

    def test_paginated_courses_include_their_own_instructors_in_a_batch(self):
        instructors = [self.instructor] + [self.models.User(
            username=f"instructor{index}", email=f"instructor{index}@example.com",
            password="private-password-hash",
        ) for index in range(3)]
        for index, instructor in enumerate(instructors):
            instructor.courses.append(self.models.Course(name=f"Course {index}"))
        self.database.add_all(instructors)
        self.database.commit()
        expected_instructors = {
            instructor.id: {"id": instructor.id, "username": instructor.username, "email": instructor.email}
            for instructor in instructors
        }
        expected_course_ids = sorted(course.id for instructor in instructors for course in instructor.courses)
        self.database.expunge_all()
        statements = []

        def capture_statement(connection, cursor, statement, parameters, context, many):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", capture_statement)
        try:
            response = self.client.get("/courses/", params={"skip": 1, "limit": 3})
        finally:
            event.remove(self.engine, "before_cursor_execute", capture_statement)

        self.assertEqual(response.status_code, 200, response.text)
        courses = response.json()
        self.assertEqual([course["id"] for course in courses], expected_course_ids[1:4])
        for course in courses:
            self.assertEqual(course["instructor"], expected_instructors[course["instructor_id"]])
            self.assertNotIn("courses", course["instructor"])
        self.assertNotIn("password", response.text)
        self.assertNotIn("private-password-hash", response.text)
        self.assertEqual(len(statements), 2)

    def test_missing_course_returns_not_found(self):
        response = self.client.get("/courses/999")
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"detail": "Course not found"})

    def test_paginates_courses_in_id_order(self):
        courses = [self.models.Course(
            id=3 * (index + 1), name=f"Course {index}", instructor_id=self.instructor.id,
        ) for index in reversed(range(5))]
        self.database.add_all(courses)
        self.database.commit()
        expected_ids = sorted(course.id for course in courses)

        for skip, expected in ((0, expected_ids[:2]), (2, expected_ids[2:4]), (4, expected_ids[4:])):
            with self.subTest(skip=skip):
                response = self.client.get("/courses/", params={"skip": skip, "limit": 2})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([course["id"] for course in response.json()], expected)

    def test_defaults_to_twenty_courses_and_accepts_the_maximum_limit(self):
        courses = [self.models.Course(
            name=f"Course {index}", instructor_id=self.instructor.id,
        ) for index in range(25)]
        self.database.add_all(courses)
        self.database.commit()
        expected_ids = sorted(course.id for course in courses)

        for params, expected in (({}, expected_ids[:20]), ({"skip": 20}, expected_ids[20:]),
                                 ({"limit": 100}, expected_ids)):
            with self.subTest(params=params):
                response = self.client.get("/courses/", params=params)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual([course["id"] for course in response.json()], expected)

    def test_pagination_beyond_the_last_course_returns_an_empty_list(self):
        self.client.post("/courses/", json=self.payload)
        for skip in (1, 999):
            with self.subTest(skip=skip):
                response = self.client.get("/courses/", params={"skip": skip})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), [])

    def test_rejects_invalid_course_pagination_parameters(self):
        for params in ({"skip": -1}, {"limit": 0}, {"limit": -1}, {"limit": 101},
                       {"skip": "invalid"}, {"limit": "invalid"}):
            with self.subTest(params=params):
                response = self.client.get("/courses/", params=params)
                self.assertEqual(response.status_code, 422, response.text)

    def test_creation_requires_a_positive_instructor_id(self):
        missing_id = {key: value for key, value in self.payload.items() if key != "instructor_id"}
        for payload in (
            missing_id,
            *({**self.payload, "instructor_id": value} for value in (None, 0, -1)),
        ):
            with self.subTest(payload=payload):
                response = self.client.post("/courses/", json=payload)
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.database.query(self.models.Course).count(), 0)

    def test_unknown_instructor_returns_not_found(self):
        response = self.client.post(
            "/courses/", json={**self.payload, "instructor_id": 999}
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json(), {"detail": "Instructor not found"})
        self.assertEqual(self.database.query(self.models.Course).count(), 0)

    def test_update_preserves_an_omitted_instructor(self):
        created = self.client.post("/courses/", json=self.payload).json()
        update = {"name": "Updated", "description": "Tutorial", "price": 20.0}

        response = self.client.put(f"/courses/{created['id']}", json=update)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "Updated")
        self.assertEqual(response.json()["instructor_id"], self.instructor.id)

    def test_update_rejects_null_or_unknown_instructors(self):
        created = self.client.post("/courses/", json=self.payload).json()
        for instructor_id, status_code in ((None, 422), (0, 422), (-1, 422), (999, 404)):
            with self.subTest(instructor_id=instructor_id):
                response = self.client.put(
                    f"/courses/{created['id']}",
                    json={**self.payload, "instructor_id": instructor_id},
                )
                self.assertEqual(response.status_code, status_code, response.text)
                stored = self.database.get(self.models.Course, created["id"])
                self.assertEqual(stored.instructor_id, self.instructor.id)

    def test_update_can_assign_an_existing_instructor(self):
        created = self.client.post("/courses/", json=self.payload).json()
        other = self.models.User(username="other", email="other@example.com", password="test-hash")
        self.database.add(other)
        self.database.commit()

        response = self.client.put(
            f"/courses/{created['id']}", json={**self.payload, "instructor_id": other.id}
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["instructor_id"], other.id)

    def test_constraint_conflicts_roll_back_the_session(self):
        for method in ("post", "put"):
            with self.subTest(method=method):
                if method == "put":
                    created = self.client.post("/courses/", json=self.payload).json()
                    url = f"/courses/{created['id']}"
                else:
                    url = "/courses/"
                with (
                    patch.object(self.database, "commit", side_effect=IntegrityError(
                        "INSERT", {}, Exception("private-database-error")
                    )),
                    patch.object(self.database, "rollback", wraps=self.database.rollback) as rollback,
                ):
                    response = getattr(self.client, method)(url, json=self.payload)
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json(), {"detail": "Course could not be saved"})
                rollback.assert_called_once()
                self.assertTrue(self.database.is_active)
                self.assertEqual(self.client.get("/courses/").status_code, 200)

    def test_openapi_marks_creation_instructor_as_required(self):
        schema = self.client.get("/openapi.json").json()
        request_schema = schema["components"]["schemas"]["CourseCreateRequest"]
        self.assertIn("instructor_id", request_schema["required"])
        self.assertEqual(request_schema["properties"]["instructor_id"]["type"], "integer")

    def test_openapi_documents_course_pagination(self):
        schema = self.client.get("/openapi.json").json()
        parameters = {parameter["name"]: parameter["schema"]
                      for parameter in schema["paths"]["/courses/"]["get"]["parameters"]}
        self.assertEqual(parameters["skip"]["default"], 0)
        self.assertEqual(parameters["skip"]["minimum"], 0)
        self.assertEqual(parameters["limit"]["default"], 20)
        self.assertEqual(parameters["limit"]["minimum"], 1)
        self.assertEqual(parameters["limit"]["maximum"], 100)

    def test_openapi_documents_instructors_on_course_fetches(self):
        schema = self.client.get("/openapi.json").json()
        list_schema = schema["paths"]["/courses/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        detail_schema = schema["paths"]["/courses/{course_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(list_schema["items"]["$ref"], "#/components/schemas/CourseResponse")
        self.assertEqual(detail_schema["$ref"], "#/components/schemas/CourseResponse")
        instructor_schema = schema["components"]["schemas"]["CourseResponse"]["properties"]["instructor"]
        self.assertIn({"$ref": "#/components/schemas/UserResponse"}, instructor_schema["anyOf"])
        user_properties = schema["components"]["schemas"]["UserResponse"]["properties"]
        self.assertEqual(set(user_properties), {"id", "username", "email"})
