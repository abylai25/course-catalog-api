"""check_models.py — compare SQLAlchemy model metadata against the live database.

Prints row counts for each table, then reports any constraint/index names that
exist only in models (not yet migrated) or only in the database (dropped from
models but still in the DB).

Run:  python check_models.py
Expected output after a clean `alembic upgrade head` + seed:
    courses: 6 rows
    students: 3 rows
    enrollments: 6 rows
    names only in models: none
    names only in database: none
"""

from sqlalchemy import select, text

from db import Base, SessionLocal

# Import models so that Base.metadata is populated with table definitions.
import models  # noqa: F401 — side-effect import required

# Query that collects all constraint and index names from the public schema.
DB_NAMES_SQL = """
SELECT conname AS name
  FROM pg_constraint
 WHERE connamespace = 'public'::regnamespace
   AND contype IN ('p', 'u', 'f', 'c')
UNION
SELECT indexname AS name
  FROM pg_indexes
 WHERE schemaname = 'public'
"""

with SessionLocal() as db:
    for model in (models.Course, models.Student, models.Enrollment):
        count = len(db.scalars(select(model)).all())
        print(f"{model.__tablename__}: {count} rows")

    in_db = {
        name
        for name in db.scalars(text(DB_NAMES_SQL))
        if not name.startswith("alembic")
    }

# Collect all constraint and index names defined in models.
in_models: set[str] = set()
for table in Base.metadata.tables.values():
    for constraint in table.constraints:
        if constraint.name:
            in_models.add(constraint.name)
    for index in table.indexes:
        if index.name:
            in_models.add(index.name)

print("names only in models:", sorted(in_models - in_db) or "none")
print("names only in database:", sorted(in_db - in_models) or "none")
