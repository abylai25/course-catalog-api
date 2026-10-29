# Course Catalog API

FastAPI backend for the course catalog, using PostgreSQL, SQLAlchemy 2.1, and
Alembic migrations.

## How to run

Requirements: Python 3.11 or newer and PostgreSQL 16 or newer.

Create the application role once as the PostgreSQL superuser:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
```

Recreate the training database (this permanently deletes its current contents):

```sql
DROP DATABASE IF EXISTS course_catalog WITH (FORCE);
CREATE DATABASE course_catalog OWNER catalog_app;
```

From the project directory, create the environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to the connection URL for your local role and
database. The training default is:

```text
DATABASE_URL=postgresql+psycopg://catalog_app:change-me@localhost:5432/course_catalog
```

Build the schema, load the initial data, and verify that models and schema match:

```powershell
alembic upgrade head
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
alembic check
```

Start the API:

```powershell
fastapi dev main.py
```

Interactive API documentation: <http://localhost:8000/docs>. To check the five
expected database/validation errors while the server is running, use a second
terminal and run `python try_errors.py`.

The password in `.env.example` is only a local teaching value. Do not commit
`.env` or use this password in a shared or production environment.

## What changed in the API

- Catalog data and likes persist in PostgreSQL across server restarts.
- `GET /courses` supports `is_elective`, `level`, `sort=popular|title`,
  `page`, and `page_size` query parameters.
- `GET /courses/{course_id}` reads a course by its primary key.
- `POST /courses/{course_id}/like` increments likes atomically in PostgreSQL.
- `POST /students` creates a student (`name`, `email`); invalid names or email
  addresses are rejected before reaching the database.
- `POST /enrollments` now takes `courseId` and `studentId`, not `studentName`.
- `GET /enrollments` joins courses and students and includes `courseTitle` and
  `studentName`.
- `GET /stats/courses` returns enrollment counts for every course, including
  courses with no enrollments.
- Constraint violations return `409` for duplicate email/enrollment and `404`
  for unknown course/student foreign keys. A request with a name shorter than
  two characters returns `422`.
- Requests and responses use camelCase JSON fields. Pydantic schemas live in
  `schemas.py`; SQLAlchemy table mappings live in `models.py`.

The existing Lab 5 frontend still submits `studentName` and is not changed by
this lab; use `/docs` or update the client to create a student and send
`studentId`.

## Migrations

| Alembic command | What it does |
|---|---|
| `alembic upgrade head` | Applies every migration not yet applied to this database. |
| `alembic downgrade -1` | Rolls back the most recent migration. |
| `alembic current` | Shows the database's current revision. |
| `alembic history` | Shows the migration history. |
| `alembic heads` | Lists current migration heads; normally there should be one. |
| `alembic revision --autogenerate -m "text"` | Creates a draft migration from model/schema differences; review it before applying. |
| `alembic check` | Fails if model metadata and the live schema differ. |
| `alembic upgrade 0001:0002 --sql` | Prints the SQL for this revision range without running it. |
| `alembic stamp head` | Records a revision without applying schema changes; use only when adopting an already matching schema. |

The pre-existing Lab 6 database was checked against the models, stamped at
`0001` without recreating its tables, then upgraded to `0002`. A brand-new
database must use `alembic upgrade head`, not `stamp`.

## Experiment log

The deliberate breakages below were tested against the local training database.
Temporary model/metadata or migration changes were restored after each test.

| # | What I did | What I saw | Cause | How I fixed it |
|---|---|---|---|---|
| 1 | Changed the `uq` naming template to use only the first column and `_unique`. | Models produced `students_email_unique` and `enrollments_course_id_unique`; PostgreSQL has `students_email_key` and `enrollments_course_id_student_id_key`. | The generated names no longer matched PostgreSQL's names for unique constraints. Alembic and the API's error map depend on exact names. | Restored `%(table_name)s_%(column_0_N_name)s_key`. |
| 2 | Inserted a one-character student name directly through the ORM, simulating a request without Pydantic's `min_length=2`. | PostgreSQL rejected the insert with `students_name_check`; because this constraint is not in the API error map, the same unvalidated request would produce HTTP 500. | Removing request validation lets the request reach the database, and the check constraint is not an API validation response. | Kept `Field(min_length=2)` so invalid input returns 422; retained the database check as a final integrity guarantee. |
| 3 | Renamed the mapped key `students_email_key` to the typo `students_email_uniq`. | A duplicate-email request returned HTTP 500 instead of 409. | The actual driver constraint name no longer matched `CONSTRAINT_ERRORS`. | Restored the exact database constraint name. |
| 4 | Dropped `NOT NULL` from `courses.title`, then changed its type to `varchar(100)`. | `alembic check` reported `modify_nullable` and `modify_type` differences and exited unsuccessfully. | The live schema no longer matched the required `Text NOT NULL` model column. | Restored `NOT NULL` and `text`; `alembic check` returned “No new upgrade operations detected.” |
| 5 | Tried adding a required column without a default to populated `courses`. | PostgreSQL raised `NotNullViolation`: existing rows had no value for the new column; the transaction left no column behind. | Existing rows must be populated before the column can become non-nullable. | Used migration `0002` to add nullable, backfill, and then set `NOT NULL`. |
| 6 | Compared the database against empty target metadata (simulating a missing `import models` in `env.py`). | Alembic proposed dropping `courses`, `students`, and `enrollments` (and their index). | With no imported models, `Base.metadata` is empty, so every live table appears obsolete. | Restored the `import models` in `alembic/env.py`; read generated migrations before applying them. |
| 7 | Added a temporary nullable `Student.phone` column to comparison metadata, without a migration. | `alembic check` comparison detected an `add_column` operation for `students.phone`. | The model describes a column that the database and migration history do not contain. | Removed the temporary field; model changes must be committed with their migration. |
| 8 | Created two temporary revisions branching from `0002`. | `alembic heads` showed `0003` and `0004`; `alembic upgrade head` failed with “Multiple head revisions”. A merge revision produced one head. | Alembic cannot choose between two independent heads automatically. | Tested the merge, then removed all temporary revisions; the project retains only `0001` and `0002`. |

## Decisions

- **Constraint names, not only SQLSTATE:** SQLSTATE identifies a broad class of
  failure (for example, unique violation), but the constraint name identifies
  which rule failed. That lets the API distinguish duplicate email,
  duplicate enrollment, and missing foreign-key targets. Unknown integrity
  errors are re-raised rather than disguised as client errors. Errors are
  handled after `commit()` because a preflight `SELECT` is vulnerable to a
  race: another request can claim the email between the check and insert.
- **Atomic likes:** `UPDATE courses SET likes = likes + 1` makes the database
  perform the increment against the current row value. Concurrent requests
  serialize their row updates instead of reading the same old value and
  overwriting one another (a lost update).
- **Three-step `level` migration:** A required column cannot be added to a
  populated table without values for existing rows. Migration `0002` adds it
  nullable, assigns `beginner` to electives and `intermediate` to other
  courses, and then enforces `NOT NULL`. Its downgrade drops the column and
  therefore discards level values; the downgrade/upgrade cycle was tested.
- **Renames and drops:** A true column rename should use
  `op.alter_column(..., new_column_name=...)` so the stored values survive.
  Dropping the old column and adding a new one loses the old values and should
  only be used when that loss is intentional.
- **Relationship loading:** Lazy-loading enrollments inside a course loop
  creates N+1 queries. `selectinload` fetches the parent rows and then related
  rows in one additional query; `joinedload` uses a join and can duplicate
  parent rows in the result, so collection results need deduplication.
- **`passive_deletes=True`:** The database owns `ON DELETE CASCADE` for a
  student's enrollments. Passive deletes prevent SQLAlchemy from first trying
  to set the required `student_id` to `NULL`, and let PostgreSQL perform the
  configured cascade.

## Migration 0002 self-check

| Check | Result | Note |
|---|---|---|
| Goal and steps are clear. | Yes | Add the required course difficulty level in three deliberate phases. |
| Existing data is handled before `NOT NULL`. | Yes | Existing electives become `beginner`; other courses become `intermediate`. |
| The migration does not disguise a rename as drop/add. | Yes | It adds a genuinely new field; no existing column is renamed or dropped. |
| Downgrade behavior is understood. | Yes | Downgrade removes `level` and any values stored in it. |
| Generated SQL was reviewed. | Yes | `alembic upgrade 0001:0002 --sql` showed add, backfill, and set-not-null in order. |
| Upgrade, downgrade, and upgrade were tested. | Yes | The database returned to `0002`; `alembic check` was clean afterwards. |
| History and application state are consistent. | Yes | One head remains; ORM and response schema both include `level`. |
