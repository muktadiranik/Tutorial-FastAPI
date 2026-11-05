import importlib
import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


class CourseInstructorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = importlib.import_module("7.app.models")

    def setUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self.models.Base.metadata.create_all(self.engine)
        self.database = sessionmaker(bind=self.engine)()
        self.addCleanup(self.database.close)
        self.user = self.models.User(
            username="instructor",
            email="instructor@example.com",
            password="test-password-hash",
        )

    def test_relationship_persists_instructor_id(self):
        course = self.models.Course(name="FastAPI", instructor=self.user)
        self.assertIn(course, self.user.courses)
        self.database.add(course)
        self.database.commit()
        self.database.expire_all()

        stored = self.database.query(self.models.Course).one()
        self.assertEqual(stored.instructor_id, self.user.id)
        self.assertIs(stored.instructor, self.user)
        self.assertIn(stored, self.user.courses)

    def test_foreign_key_requires_an_existing_instructor(self):
        for instructor_id in (None, 999):
            with self.subTest(instructor_id=instructor_id):
                course = self.models.Course(
                    name="FastAPI", instructor_id=instructor_id
                )
                self.database.add(course)
                with self.assertRaises(IntegrityError):
                    self.database.commit()
                self.database.rollback()

    def test_removing_course_deletes_orphan(self):
        course = self.models.Course(name="FastAPI")
        self.user.courses.append(course)
        self.assertIs(course.instructor, self.user)
        self.database.add(self.user)
        self.database.commit()

        self.user.courses.remove(course)
        self.database.commit()

        self.assertEqual(self.database.query(self.models.Course).count(), 0)
        self.assertEqual(self.database.query(self.models.User).count(), 1)

    def test_deleting_instructor_deletes_courses(self):
        self.user.courses.append(self.models.Course(name="FastAPI"))
        self.database.add(self.user)
        self.database.commit()

        self.database.delete(self.user)
        self.database.commit()

        self.assertEqual(self.database.query(self.models.Course).count(), 0)
        self.assertEqual(self.database.query(self.models.User).count(), 0)
