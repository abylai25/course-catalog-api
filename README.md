# Course Catalog API

A FastAPI backend that exposes a course catalog with filtering, sorting, pagination, likes, and enrollment.

## How to Run

```bash
# 1. Create and activate the virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the development server
fastapi dev main.py
```

The server starts at **http://127.0.0.1:8000**.  
Interactive docs: **http://127.0.0.1:8000/docs**

## CORS

The middleware allows requests from `http://localhost:3000` (the Next.js dev server).  
All HTTP methods and headers are permitted.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## JSON Key Casing

All request and response bodies use **camelCase** keys (e.g. `courseId`, `studentName`, `isElective`).  
This is achieved via `CamelModel` — a shared `BaseModel` subclass with `alias_generator=to_camel`.  
Snake-case field names are still accepted on input thanks to `validate_by_name=True`.

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/courses` | Course list with filtering, sorting, pagination |
| GET | `/courses/{course_id}` | Single course or 404 |
| POST | `/courses/{course_id}/like` | Increment like counter, returns updated course |
| POST | `/enrollments` | Enroll a student in a course (201 Created) |
| GET | `/enrollments` | List all in-memory enrollments |

### POST /courses/{course_id}/like

Returns the updated `Course` object with the incremented `likes` field.  
Responds with **404** if the course does not exist.

**Example response:**
```json
{
  "id": "web-security",
  "title": "Web Security Essentials",
  "description": "JWT/OAuth2, XSS, CSRF, and SQL injection defense.",
  "credits": 4,
  "isElective": false,
  "likes": 22
}
```

### POST /enrollments

**Request body (camelCase):**
```json
{
  "courseId": "web-security",
  "studentName": "Alice"
}
```

**Validation:**
- `studentName` must be at least 2 characters (returns **422** otherwise).
- `courseId` must match an existing course (returns **404** otherwise).

**Response (201 Created):**
```json
{
  "id": 1,
  "courseId": "web-security",
  "studentName": "Alice"
}
```

### GET /enrollments

Returns an array of all `Enrollment` objects stored in memory since the server started.

## Project Structure

```
course-catalog-api/
├── .venv/            # virtual environment — not in git
├── .gitignore
├── README.md
├── requirements.txt
├── models.py         # CamelModel, Course, Stats, EnrollmentIn, Enrollment
├── data.py           # 6 courses + get_all_courses / find_course helpers
└── main.py           # FastAPI app, CORS, all routes
```
