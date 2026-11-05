"""Alembic environment configuration.

Connects the migration runner to the application's models and settings so
that --autogenerate can compare SQLAlchemy metadata with the live schema.

NullPool is used for migrations: each migration step opens a fresh connection
and closes it immediately, which is safe for long-running scripts and avoids
holding a pool connection open across DDL transactions.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import models so that Base.metadata is populated with all table definitions.
# Without this import Base.metadata is empty and autogenerate proposes dropping
# every table in the database.
import models  # noqa: F401 — side-effect import required

from config import settings
from db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live database connection.

    Useful for generating SQL scripts to review before applying.
    """
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the live database using a fresh NullPool engine."""
    # Override the sqlalchemy.url from alembic.ini with the value from .env.
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
