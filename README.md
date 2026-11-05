# Course Catalog API — Lab 7

**Student:** Shakir Abylai  
**Group:** IT3-2302  
**Stack:** Python 3.11 · FastAPI · SQLAlchemy 2.1 · PostgreSQL 16 · Alembic

FastAPI backend for the course catalog.  Migrated from an in-memory store to
PostgreSQL with full ORM models, Alembic migrations, and structured error
handling for constraint violations.

---

## Table of Contents

1. [How to run](#1-how-to-run)
2. [What changed in the API](#2-what-changed-in-the-api)
3. [Migrations](#3-migrations)
4. [Experiment log](#4-experiment-log)
5. [Decisions](#5-decisions)
6. [Migration 0002 self-check](#6-migration-0002-self-check)

---

## 1. How to run

### Prerequisites

- Python 3.11 or newer
- PostgreSQL 16 or newer running locally
- `psql` CLI available in PATH

### 1.1 Create the database role and database

Connect as the PostgreSQL superuser (e.g. `postgres`) and run once:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
DROP DATABASE IF EXISTS course_catalog WITH (FORCE);
CREATE DATABASE course_catalog OWNER catalog_app;
```

### 1.2 Create the virtual environment and install dependencies

```powershell
cd course-catalog-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 1.3 Configure environment variables

```powershell
Copy-Item .env.example .env
```

Open `.env` and verify `DATABASE_URL` points to your local database:

```text
DATABASE_URL=postgresql+psycopg://catalog_app:change-me@localhost:5432/course_catalog
SQL_ECHO=false
```

### 1.4 Apply migrations and load seed data

```powershell
# Apply all migrations from scratch
alembic upgrade head

# Verify the schema matches the models
alembic check

# Load initial courses, students, and enrollments
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
```

### 1.5 Verify connectivity and model/schema alignment

```powershell
python check_db.py
# connected to course_catalog as catalog_app, PostgreSQL 16.x

python check_models.py
# courses: 6 rows
# students: 3 rows
# enrollments: 6 rows
# names only in models: none
# names only in database: none
```

### 1.6 Start the development server

```powershell
fastapi dev main.py
```

Interactive API docs: <http://localhost:8000/docs>

### 1.7 Run error-handling smoke tests

With the server running, open a second terminal:

```powershell
python try_errors.py
# ok   email already taken     409  ...
# ok   already enrolled        409  ...
# ok   unknown course          404  ...
# ok   unknown student         404  ...
# ok   name too short          422  ...
# 5 of 5 as expected
```

### 1.8 Adopt an existing Lab 6 database (optional)

If the database already has the correct schema from Lab 6, stamp it instead of
re-creating it, then apply only the new migration:

```powershell
alembic stamp 0001
alembic upgrade head    # applies only 0002
alembic check           # should report no differences
```

> **Security note:** The password `change-me` is a local teaching value only.
> Never commit `.env` or reuse this password in a shared environment.

---

## 2. What changed in the API

### Persistence

Course data and like counters now persist in PostgreSQL across server restarts.
The in-memory `COURSES` dictionary and all ad-hoc list manipulation have been
removed.

### New and changed endpoints

| Endpoint | Change |
|---|---|
| `GET /courses` | Reads from DB; supports `is_elective`, `level`, `sort=popular\|title`, `page`, `page_size`. |
| `GET /courses/{id}` | Uses `db.get(Course, id)` — a PK lookup; returns 404 for unknown ids. |
| `POST /courses/{id}/like` | Increments likes atomically with `UPDATE … SET likes = likes + 1 RETURNING *`. |
| `POST /students` | New endpoint — creates a student with `name` and `email`. |
| `POST /enrollments` | Now accepts `courseId` + `studentId` (not `studentName`). |
| `GET /enrollments` | Inner-joins courses and students; returns `courseTitle` and `studentName`. |
| `GET /stats/courses` | New endpoint — enrollment counts via LEFT JOIN + GROUP BY. |

### Error handling

| Situation | HTTP status | Trigger |
|---|---|---|
| Duplicate student email | 409 | `students_email_key` unique constraint |
| Student already enrolled | 409 | `enrollments_course_id_student_id_key` unique constraint |
| Unknown `course_id` FK | 404 | `enrollments_course_id_fkey` FK constraint |
| Unknown `student_id` FK | 404 | `enrollments_student_id_fkey` FK constraint |
| `name` shorter than 2 chars | 422 | Pydantic `Field(min_length=2)` |

### New `level` field

`GET /courses` and `GET /courses/{id}` now return `level` (`beginner` /
`intermediate` / `advanced`).  Added by migration `0002`.

### camelCase JSON

All request and response bodies use camelCase keys (`courseId`, `studentId`,
`enrolledAt`, etc.).  Python model fields remain snake_case; the alias
generator in `CamelModel` performs the conversion transparently.

---

## 3. Migrations

### Reference table of Alembic commands

| Command | What it does |
|---|---|
| `alembic upgrade head` | Applies every unapplied migration in order. |
| `alembic upgrade +1` | Applies exactly one migration above the current revision. |
| `alembic downgrade -1` | Rolls back the most recent migration. |
| `alembic downgrade base` | Rolls back all migrations (full teardown). |
| `alembic current` | Prints the current revision stored in `alembic_version`. |
| `alembic history` | Lists all revisions (newest first). |
| `alembic history --verbose` | Full details including docstrings. |
| `alembic heads` | Lists current head revisions; normally exactly one. |
| `alembic revision --autogenerate -m "text"` | Generates a draft migration from model/schema diff — always review before applying. |
| `alembic check` | Exits non-zero if model metadata and live schema differ. |
| `alembic upgrade 0001:0002 --sql` | Prints the SQL for migration 0002 without executing it. |
| `alembic stamp head` | Records a revision without running DDL; use when adopting a pre-existing matching schema. |
| `alembic stamp base` | Clears the recorded revision (as if no migrations were run). |
| `alembic merge -m "merge" 0003 0004` | Creates a merge revision to resolve two heads into one. |
| `alembic show 0002` | Displays full metadata for revision 0002. |

### Migration files in this project

| File | Revision | What it creates |
|---|---|---|
| `0001_create_catalog_tables.py` | `0001` | Tables `courses`, `students`, `enrollments` with all constraints, FKs, and index. |
| `0002_add_course_level.py` | `0002` | Column `courses.level TEXT NOT NULL` using the three-step nullable→backfill→NOT NULL pattern. |

---

## 4. Experiment log

Each experiment was run against the local training database.  Model or
migration changes were reverted after the experiment so the final state of the
repository is clean.

---

### Experiment 1 — Changed the `uq` naming-convention template

**What I did:**  
In `db.py` I changed the `uq` template from  
`"%(table_name)s_%(column_0_N_name)s_key"` to  
`"%(table_name)s_%(column_0_name)s_unique"`.

**What happened:**  
`alembic check` reported two `modify_constraint` differences:

```
INFO  Detected differences: [
  ('remove_constraint', <UniqueConstraint 'students_email_key'>),
  ('add_constraint', <UniqueConstraint 'students_email_unique'>),
  ('remove_constraint', <UniqueConstraint 'enrollments_course_id_student_id_key'>),
  ('add_constraint', <UniqueConstraint 'enrollments_course_id_unique'>)
]
```

`try_errors.py` failed: `students_email_unique` is not a key in
`CONSTRAINT_ERRORS`, so a duplicate-email POST returned HTTP 500 instead of
409.

**Cause:**  
`%(column_0_N_name)s` joins **all** columns in the constraint with underscores
(`course_id_student_id`); `%(column_0_name)s` uses only the first column
(`course_id`).  The names generated by the template must match the names
PostgreSQL created when the table was built by migration `0001`.

**How I fixed it:**  
Restored the original template.  `alembic check` returned "No new upgrade
operations detected."

---

### Experiment 2 — Removed `min_length=2` from `StudentIn`

**What I did:**  
In `schemas.py` I changed `name: str = Field(min_length=2)` to
`name: str`.  Then I sent `POST /students {"name": "N", "email": "n@example.com"}`.

**What happened:**  
The request passed Pydantic validation and reached SQLAlchemy.  PostgreSQL
rejected the INSERT with:

```
sqlalchemy.exc.IntegrityError: (psycopg.errors.CheckViolation)
  new row for relation "students" violates check constraint "students_name_check"
DETAIL:  Failing row contains (4, N, n@example.com).
```

Because `students_name_check` is not in `CONSTRAINT_ERRORS`, the API returned
HTTP 500 instead of 422.  The response was:

```json
{"detail": "Internal Server Error"}
```

**Cause:**  
Removing the Pydantic validator allowed the invalid value to reach the database.
The DB check constraint caught it, but that error is not mapped to an HTTP
response in the current `CONSTRAINT_ERRORS` dict.

**How I fixed it:**  
Restored `Field(min_length=2)`.  Invalid names are now rejected by Pydantic
before the database is touched; the DB check constraint remains as a
defense-in-depth guarantee.

---

### Experiment 3 — Typo in `CONSTRAINT_ERRORS` key

**What I did:**  
In `main.py` I renamed the `CONSTRAINT_ERRORS` key  
`"students_email_key"` → `"students_email_uniq"`.

**What happened:**  
Sending `POST /students` with `aigerim@example.com` (already registered)
returned HTTP 500:

```
sqlalchemy.exc.IntegrityError: (psycopg.errors.UniqueViolation)
  duplicate key value violates unique constraint "students_email_key"
DETAIL:  Key (email)=(aigerim@example.com) already exists.
```

The `raise_http_error` function looked up `"students_email_key"` in the
dictionary, didn't find it (because the key was `"students_email_uniq"`), and
re-raised the `IntegrityError` as HTTP 500.

**Cause:**  
`exc.orig.diag.constraint_name` returns the exact name PostgreSQL used when it
raised the error.  The lookup key in `CONSTRAINT_ERRORS` must be a byte-for-byte
match.

**How I fixed it:**  
Restored the exact constraint name `"students_email_key"`.

---

### Experiment 4 — Dropped `NOT NULL` from `courses.title` then ran `alembic check`

**What I did:**  
Connected with `psql` and ran:

```sql
ALTER TABLE courses ALTER COLUMN title DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN title TYPE varchar(100);
```

Then:

```powershell
alembic check
```

**What happened:**  
Alembic exited with a non-zero status and printed:

```
INFO  Detected differences: [
  ('modify_nullable', 'public', 'courses', 'title', {'existing_nullable': True, ...},
     False, True),
  ('modify_type', 'public', 'courses', 'title', {'existing_type': VARCHAR(length=100)},
     TEXT(), VARCHAR(length=100))
]
ERROR New upgrade operations detected: please run "alembic revision --autogenerate".
```

**Cause:**  
The live schema (`varchar(100)`, nullable) no longer matched the model
(`Text`, `NOT NULL`).  `alembic check` compares `target_metadata` with the
live database and reports any difference.

**How I fixed it:**  
```sql
ALTER TABLE courses ALTER COLUMN title SET NOT NULL;
ALTER TABLE courses ALTER COLUMN title TYPE text;
```
`alembic check` then returned "No new upgrade operations detected."

---

### Experiment 5 — Tried adding a NOT NULL column to a populated table in one step

**What I did:**  
Wrote a **single-step** migration that added `level TEXT NOT NULL` directly:

```python
op.add_column("courses", sa.Column("level", sa.Text(), nullable=False))
```

Applied it to the database that already had 6 course rows from `seed.sql`.

**What happened:**  
The migration failed immediately:

```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.NotNullViolation)
  column "level" of relation "courses" contains null values
```

The table was left unchanged (PostgreSQL rolls back DDL on error).

**Cause:**  
PostgreSQL cannot add a `NOT NULL` column to a table that already has rows
unless a `DEFAULT` expression can populate every existing row.  Without a
`DEFAULT`, the new column value for every existing row would be `NULL`, which
immediately violates the constraint.

**How I fixed it:**  
Rewrote the migration as the three-step pattern used in `0002`:
1. Add the column as `nullable=True`.
2. `UPDATE courses SET level = …` to back-fill every row.
3. `ALTER COLUMN level SET NOT NULL`.

---

### Experiment 6 — Commented out `import models` in `alembic/env.py`

**What I did:**  
In `alembic/env.py` I commented out the line `import models`.

Then ran:

```powershell
alembic revision --autogenerate -m "empty test"
```

**What happened:**  
Alembic generated a migration file that proposed dropping every table:

```python
def upgrade() -> None:
    op.drop_index("enrollments_student_id_idx", ...)
    op.drop_table("enrollments")
    op.drop_table("students")
    op.drop_table("courses")

def downgrade() -> None:
    pass
```

**Cause:**  
Without the `import models` line, `Base.metadata` contains no table
definitions at the time Alembic runs.  Alembic compares an empty
`target_metadata` with the live database (which has three tables) and concludes
that all three tables are obsolete.

**How I fixed it:**  
Restored `import models` and deleted the erroneous revision file.  This is why
every generated migration must be reviewed before `alembic upgrade head`.

---

### Experiment 7 — Added `Student.phone` to the model without a migration

**What I did:**  
In `models.py` I added a column to the `Student` class:

```python
phone: Mapped[str | None] = mapped_column(nullable=True)
```

Then ran `alembic check`.

**What happened:**  

```
INFO  Detected differences: [('add_column', 'public', 'students', Column('phone', Text(), ...))]
ERROR New upgrade operations detected: please run "alembic revision --autogenerate".
```

The application itself also behaved incorrectly: any ORM query that loaded a
`Student` raised `CompileError` because SQLAlchemy tried to SELECT a column that
does not exist in the database.

**Cause:**  
The model describes the database schema.  When they diverge, both Alembic and
the ORM detect the inconsistency.

**How I fixed it:**  
Removed the `phone` field from the model.  `alembic check` became clean again.
The correct workflow is: add the field to the model **and** create a migration
at the same time, then apply the migration.

---

### Experiment 8 — Created two migration branches from the same ancestor

**What I did:**  
With `0002` as the current head, I generated two migrations in sequence without
applying either, creating branches from the same parent:

```powershell
alembic revision -m "branch A"   # → 0003a, down_revision="0002"
alembic revision -m "branch B"   # → 0003b, down_revision="0002"
```

Then ran `alembic heads`:

```
0003a (head)
0003b (head)
```

And `alembic upgrade head` failed:

```
ERROR Multiple head revisions are present for given argument 'head'; please specify
a specific target revision, '<branchname>@head' to narrow to a specific branch,
or 'heads' for all heads
```

**Cause:**  
Alembic's linear-history model requires a single head.  When two revisions share
the same `down_revision`, the graph has a fork and `head` is ambiguous.

**How I fixed it:**  
Created a merge revision to reunite the two branches:

```powershell
alembic merge -m "merge A and B" 0003a 0003b
# → 0004_merge (down_revision=("0003a", "0003b"))
alembic upgrade head   # now succeeds
```

Then deleted all three temporary revisions (`0003a`, `0003b`, `0004_merge`).
The repository keeps only `0001` and `0002`.

---

## 5. Decisions

### Why constraint names instead of SQLSTATE after `commit()`?

SQLSTATE `23505` identifies any unique-constraint violation, and `23503` covers
any foreign-key violation.  Neither tells you **which** constraint was violated.
The API needs to distinguish:

- duplicate email → 409 "Student with this email already exists"
- duplicate enrollment → 409 "Student is already enrolled in this course"
- missing course FK → 404 "Course not found"
- missing student FK → 404 "Student not found"

Only the constraint name carries that information.  `exc.orig.diag.constraint_name`
is the exact name PostgreSQL used when raising the error, so it is a reliable
key.

A preflight SELECT (`SELECT 1 FROM students WHERE email = ?`) before the INSERT
looks safe but creates a **TOCTOU race condition**: a concurrent request can
insert the same email between the SELECT and the INSERT.  Only the database's
UNIQUE constraint enforces atomicity.

Unknown integrity errors (constraint names not in `CONSTRAINT_ERRORS`) are
re-raised rather than converted to a generic 4xx response.  That makes them
visible as HTTP 500 during development and prevents the server from silently
hiding unexpected database problems.

---

### Why is the like counter incremented with `UPDATE … SET likes = likes + 1`?

Consider two concurrent `POST /courses/ai-integration/like` requests:

1. Both read `likes = 31` from the database (via `db.get()` or a SELECT).
2. Both compute `new_likes = 31 + 1 = 32`.
3. Both write `likes = 32`.

Result: two likes, but the counter only moves from 31 to 32.  That is the
**lost-update** anomaly.

`UPDATE courses SET likes = likes + 1` lets PostgreSQL perform the increment.
The database serializes the two row updates: one transaction reads and writes
31 → 32, the other reads and writes 32 → 33.  No update is lost.

Using `.returning(Course)` folds the subsequent SELECT into the same round-trip,
so the response contains the up-to-date row without an extra query.

---

### Why is migration `0002` split into three steps?

PostgreSQL does not allow adding a `NOT NULL` column to a non-empty table in one
statement unless you also supply a `DEFAULT` expression — because PostgreSQL must
determine the column value for every existing row immediately.  A constant
default would be wrong here: the value depends on `is_elective`, which varies
per row.

The three-step approach is the standard solution:

| Step | SQL | Purpose |
|---|---|---|
| 1 | `ADD COLUMN level TEXT` | Column exists; existing rows get `NULL` (valid because no NOT NULL yet). |
| 2 | `UPDATE courses SET level = CASE …` | Every row receives a meaningful value derived from existing data. |
| 3 | `ALTER COLUMN level SET NOT NULL` | No row is NULL; constraint is now safe to enforce. |

This pattern works on a live database with zero downtime: step 1 is a fast
metadata change, step 2 is a table scan, step 3 is a fast constraint add once
all values are present.

---

## 6. Migration 0002 self-check

| Check | Result | Note |
|---|---|---|
| The goal and all three steps are clearly documented. | ✅ Yes | Docstring in `0002_add_course_level.py` explains each step and its purpose. |
| Existing rows are back-filled before `NOT NULL` is enforced. | ✅ Yes | Step 2 sets `level` on every existing row; step 3 then sets `NOT NULL`. |
| The migration does not disguise a rename as drop + add. | ✅ Yes | `level` is a genuinely new field; no existing column is renamed or dropped. |
| The downgrade behavior is understood and accepted. | ✅ Yes | `downgrade()` drops the column; level values are intentionally discarded on rollback. |
| The generated SQL was reviewed before applying. | ✅ Yes | `alembic upgrade 0001:0002 --sql` showed the three statements in the correct order. |
| Upgrade → downgrade → upgrade cycle was tested successfully. | ✅ Yes | DB returned to `0002`; `alembic check` was clean; `check_models.py` reported no differences. |
| History is linear with a single head after the migration. | ✅ Yes | `alembic heads` reports one head (`0002`); `alembic history` shows `0001 → 0002`. |

---

## Git commit history

```
Add database settings and engine
Move Pydantic models to schemas.py
Add SQLAlchemy models
Rewrite course routes on SQLAlchemy
Add students, enrollments and course statistics
Map constraint violations to HTTP errors
Add Alembic and the initial migration
Add course level with a three-step migration
Add README with migration notes
```
