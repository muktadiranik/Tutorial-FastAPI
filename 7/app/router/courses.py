import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..database import get_database
from ..models import Course, User
from ..schemas import (
    CourseCreateRequest,
    CourseRequest,
    CourseResponse,
    CourseResponseBulk,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/courses", tags=["Courses"])
DatabaseDep = Annotated[Session, Depends(get_database)]


@router.get("/", response_model=list[CourseResponse])
def get_courses(
    database: DatabaseDep,
    skip: Annotated[int, Query(
        ge=0, description="Number of courses to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=100, description="Maximum courses to return")] = 20,
) -> list[Course]:
    """Return a page of courses with their instructors, ordered by ID."""
    courses = (
        database.query(Course)
        .options(selectinload(Course.instructor))
        .order_by(Course.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    logger.debug("Courses retrieved count=%s", len(courses))
    return courses


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, database: DatabaseDep):
    course = database.query(Course).filter(Course.id == course_id).options(
        selectinload(Course.instructor)).first()
    if not course:
        logger.warning("Course not found course_id=%s", course_id)
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/", response_model=CourseResponseBulk)
def create_course(course: CourseCreateRequest, database: DatabaseDep):
    if database.get(User, course.instructor_id) is None:
        raise HTTPException(status_code=404, detail="Instructor not found")

    new_course = Course(
        name=course.name,
        description=course.description,
        price=course.price,
        instructor_id=course.instructor_id,
    )
    database.add(new_course)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        logger.warning(
            "Course creation rejected: database constraint conflict")
        raise HTTPException(
            status_code=409, detail="Course could not be saved")
    database.refresh(new_course)
    logger.info("Course created course_id=%s", new_course.id)
    return new_course


@router.put("/{course_id}", response_model=CourseResponseBulk)
def update_course(course_id: int, course: CourseRequest, database: DatabaseDep):
    existing_course = database.query(Course).filter(
        Course.id == course_id).first()
    if not existing_course:
        logger.warning("Course not found course_id=%s", course_id)
        raise HTTPException(status_code=404, detail="Course not found")

    if "instructor_id" in course.model_fields_set:
        if course.instructor_id is None:
            raise HTTPException(
                status_code=422, detail="Instructor ID cannot be null")
        if database.get(User, course.instructor_id) is None:
            raise HTTPException(status_code=404, detail="Instructor not found")

    for key, value in course.model_dump(exclude_unset=True).items():
        setattr(existing_course, key, value)

    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        logger.warning("Course update rejected: database constraint conflict")
        raise HTTPException(
            status_code=409, detail="Course could not be saved")
    database.refresh(existing_course)
    logger.info("Course updated course_id=%s", existing_course.id)
    return existing_course


@router.delete("/{course_id}")
async def delete_course(course_id: int, database: Session = Depends(get_database)):
    existing_course = database.query(Course).filter(
        Course.id == course_id).first()
    if not existing_course:
        logger.warning("Course not found course_id=%s", course_id)
        raise HTTPException(status_code=404, detail="Course not found")

    database.delete(existing_course)
    database.commit()
    logger.info("Course deleted course_id=%s", course_id)
    return {"message": "Course deleted successfully"}
