import time
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import get_db
from models import Course, Enrollment, Student
from schemas import (
    CourseOut,
    CourseStats,
    EnrollmentDetail,
    EnrollmentIn,
    EnrollmentOut,
    StudentIn,
    StudentOut,
)

app = FastAPI(title="Course Catalog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionDep = Annotated[Session, Depends(get_db)]


def pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> tuple[int, int]:
    return (page - 1) * page_size, page_size


PaginationDep = Annotated[tuple[int, int], Depends(pagination)]

CONSTRAINT_ERRORS = {
    "students_email_key": (409, "Student with this email already exists"),
    "enrollments_course_id_student_id_key": (
        409,
        "Student is already enrolled in this course",
    ),
    "enrollments_course_id_fkey": (404, "Course not found"),
    "enrollments_student_id_fkey": (404, "Student not found"),
}


def raise_http_error(exc: IntegrityError) -> None:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name in CONSTRAINT_ERRORS:
        status_code, detail = CONSTRAINT_ERRORS[constraint_name]
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise exc


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[CourseOut])
def list_courses(
    db: SessionDep,
    page: PaginationDep,
    is_elective: bool | None = None,
    level: str | None = None,
    sort: Literal["popular", "title"] = "popular",
):
    time.sleep(0.2)
    stmt = select(Course)
    if is_elective is not None:
        stmt = stmt.where(Course.is_elective == is_elective)
    if level is not None:
        stmt = stmt.where(Course.level == level)

    if sort == "title":
        stmt = stmt.order_by(Course.title)
    else:
        stmt = stmt.order_by(Course.likes.desc())

    offset, limit = page
    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()


@app.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: SessionDep):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.post("/courses/{course_id}/like", response_model=CourseOut)
def like_course(course_id: str, db: SessionDep):
    stmt = (
        update(Course)
        .where(Course.id == course_id)
        .values(likes=Course.likes + 1)
        .returning(Course)
    )
    course = db.scalars(stmt).one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    db.commit()
    return course


@app.post("/students", response_model=StudentOut, status_code=201)
def create_student(data: StudentIn, db: SessionDep):
    student = Student(name=data.name, email=data.email)
    db.add(student)
    try:
        db.commit()
    except IntegrityError as exc:
        raise_http_error(exc)
    return student


@app.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def create_enrollment(data: EnrollmentIn, db: SessionDep):
    enrollment = Enrollment(course_id=data.course_id, student_id=data.student_id)
    db.add(enrollment)
    try:
        db.commit()
    except IntegrityError as exc:
        raise_http_error(exc)
    return enrollment


@app.get("/enrollments", response_model=list[EnrollmentDetail])
def list_enrollments(db: SessionDep):
    stmt = (
        select(
            Enrollment.id,
            Enrollment.course_id,
            Course.title.label("course_title"),
            Enrollment.student_id,
            Student.name.label("student_name"),
            Enrollment.enrolled_at,
        )
        .join(Enrollment.course)
        .join(Enrollment.student)
        .order_by(Enrollment.id)
    )
    return db.execute(stmt).mappings().all()


@app.get("/stats/courses", response_model=list[CourseStats])
def course_stats(db: SessionDep):
    stmt = (
        select(
            Course.id.label("course_id"),
            func.count(Enrollment.id).label("enrolled"),
        )
        .outerjoin(Course.enrollments)
        .group_by(Course.id)
        .order_by(Course.id)
    )
    return db.execute(stmt).mappings().all()
