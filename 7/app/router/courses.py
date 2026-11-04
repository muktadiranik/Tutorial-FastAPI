from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_database
from ..models import Course
from ..schemas import CourseRequest, CourseResponse


router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("/", response_model=list[CourseResponse])
async def get_courses(database: Session = Depends(get_database)):
    courses = database.query(Course).all()
    return courses


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(course_id: int, database: Session = Depends(get_database)):
    course = database.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/", response_model=CourseResponse)
async def create_course(course: CourseRequest, database: Session = Depends(get_database)):
    new_course = Course(
        name=course.name,
        description=course.description,
        price=course.price
    )
    database.add(new_course)
    database.commit()
    database.refresh(new_course)
    return new_course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(course_id: int, course: CourseRequest, database: Session = Depends(get_database)):
    existing_course = database.query(Course).filter(
        Course.id == course_id).first()
    if not existing_course:
        raise HTTPException(status_code=404, detail="Course not found")

    for key, value in course.model_dump().items():
        setattr(existing_course, key, value)

    database.commit()
    database.refresh(existing_course)
    return existing_course


@router.delete("/{course_id}")
async def delete_course(course_id: int, database: Session = Depends(get_database)):
    existing_course = database.query(Course).filter(
        Course.id == course_id).first()
    if not existing_course:
        raise HTTPException(status_code=404, detail="Course not found")

    database.delete(existing_course)
    database.commit()
    return {"message": "Course deleted successfully"}
