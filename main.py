from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from data import find_course, get_all_courses
from models import Course, Enrollment, EnrollmentIn, Stats

app = FastAPI(title="Course Catalog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ENROLLMENTS: list[Enrollment] = []


def pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return {"offset": (page - 1) * page_size, "limit": page_size}


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[Course])
def list_courses(
    is_elective: bool | None = None,
    sort: Literal["popular", "title"] = "popular",
    p: Annotated[dict, Depends(pagination)] = None,
):
    courses = get_all_courses()

    if is_elective is not None:
        courses = [c for c in courses if c.is_elective == is_elective]

    if sort == "title":
        courses = sorted(courses, key=lambda c: c.title)
    else:
        courses = sorted(courses, key=lambda c: c.likes, reverse=True)

    offset = p["offset"]
    limit = p["limit"]
    return courses[offset: offset + limit]


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.post("/courses/{course_id}/like", response_model=Course)
def like_course(course_id: str):
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    course.likes += 1
    return course


@app.post("/enrollments", response_model=Enrollment, status_code=201)
def enroll(data: EnrollmentIn):
    course = find_course(data.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    enrollment = Enrollment(
        id=len(ENROLLMENTS) + 1,
        course_id=data.course_id,
        student_name=data.student_name,
    )
    ENROLLMENTS.append(enrollment)
    return enrollment


@app.get("/enrollments", response_model=list[Enrollment])
def list_enrollments():
    return ENROLLMENTS
