from sqlalchemy import text

from db import engine


with engine.connect() as connection:
    database, user = connection.execute(
        text("SELECT current_database(), current_user")
    ).one()
    version = connection.execute(text("SHOW server_version")).scalar_one()

print(f"connected to {database} as {user}, PostgreSQL {version}")
