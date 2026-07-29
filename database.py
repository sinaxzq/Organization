import sqlite3
from pathlib import Path
from collections.abc import Generator
from contextlib import contextmanager

DATABASE_PATH =  Path(__file__).with_name("operations.db")

def casefold_text(value: str) -> str:
    return value.casefold()

def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    connection.create_function(
    "CASEFOLD",
    1,
    casefold_text,
    deterministic=True,
    )
    
    return connection

@contextmanager
def database_connection() -> Generator[sqlite3.Connection]:
    connection = connect_database()

    try:
        yield connection
    finally:
        connection.close()

@contextmanager
def database_transaction() -> Generator[sqlite3.Connection]:
    with database_connection() as connection:
        with connection:
            yield connection

def init_database():
    with database_transaction() as connection:
        version_row = connection.execute(
            "PRAGMA user_version"
        ).fetchone()

        if version_row is None:
            raise RuntimeError("SQLite did not return schema version")
        
        version = version_row[0]

        if version < 1:

            connection.execute(
                        """
                        CREATE TABLE IF NOT EXISTS tasks (
                            id INTEGER PRIMARY KEY,
                            title TEXT NOT NULL
                                CHECK(length(title) BETWEEN 1 AND 200),
                            status TEXT NOT NULL DEFAULT 'todo'
                                CHECK(status IN ('todo', 'in_progress', 'done'))
                        )
                        """
                    )
                        
            connection.execute("PRAGMA user_version = 1")
            version = 1

        if version < 2:
            connection.execute(
                """
                CREATE TABLE organizations (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                        CHECK(length(name) BETWEEN 1 AND 200)
                )
                """
            )

            connection.execute(
                """
                INSERT INTO organizations (id, name)
                VALUES (?, ?)
                """,
                (1, "Default Organization"),
            )

            connection.execute("PRAGMA user_version = 2")
            version = 2

        if version < 3:
            connection.execute(
                """
                CREATE TABLE tasks_new (
                    id INTEGER PRIMARY KEY,
                    organization_id INTEGER NOT NULL
                        REFERENCES organizations(id),
                    title TEXT NOT NULL
                        CHECK(length(title) BETWEEN 1 AND 200),
                    status TEXT NOT NULL DEFAULT 'todo'
                        CHECK(status IN ('todo', 'in_progress', 'done'))
                )
                """
            )

            connection.execute(
                """
                INSERT INTO tasks_new (
                    id,
                    organization_id,
                    title,
                    status
                )
                SELECT
                    id,
                    1,
                    title,
                    status
                FROM tasks
                """
            )

            connection.execute("DROP TABLE tasks")

            connection.execute(
                "ALTER TABLE tasks_new RENAME TO tasks"
            )

            connection.execute(
                """
                CREATE INDEX idx_tasks_organization_id
                ON tasks(organization_id)
                """
            )

            connection.execute("PRAGMA user_version = 3")
            version = 3

def get_tasks(
    organization_id: int,
    status: str | None = None,
    q: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[dict], int]:
    conditions = ["organization_id = ?"]
    parameters: list[object] = [organization_id]

    if status is not None:
        conditions.append("status = ?")
        parameters.append(status)

    if q is not None:
        conditions.append(
            "instr(CASEFOLD(title), CASEFOLD(?)) > 0"
        )
        parameters.append(q)

    where_clause = ""

    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    with database_connection() as connection:
        total_row = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM tasks
            {where_clause}
            """,
            parameters,
        ).fetchone()

        rows = connection.execute(
            f"""
            SELECT id, title, status
            FROM tasks
            {where_clause}
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()

    if total_row is None:
        raise RuntimeError("SQLite did not return task count")

    return (
        [dict(row) for row in rows],
        total_row["total"],
    )

def get_task(
    organization_id: int,
    task_id: int,
) -> dict | None:
    with database_transaction() as connection:
        row = connection.execute(
            """
            SELECT id, title, status
            FROM tasks
            WHERE id = ?
                AND organization_id = ?
            """,
            (task_id,organization_id),
        ).fetchone()

    if row is None:
        return None

    return dict(row)

def create_task(
    organization_id: int,
    title: str,
    status: str,
) -> dict:
    with database_transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (organization_id, title, status)
            VALUES (?, ?, ?)
            """,
            (organization_id, title, status),
        )

        task_id = cursor.lastrowid

        if task_id is None:
            raise RuntimeError("SQLite did not return a task id")

        row = connection.execute(
            """
            SELECT id, organization_id, title, status
            FROM tasks
            WHERE id = ? 
                AND organization_id = ?
            """,
            (task_id,organization_id),
        ).fetchone()

        if row is None:
            raise RuntimeError("Created task was not found")

        return dict(row)

def update_task(
    organization_id: int,
    task_id: int,
    update_data: dict,
) -> dict | None:
    assignments = []
    values = []

    for field in ("title", "status"):
        if field in update_data:
            assignments.append(f"{field} = ?")
            values.append(update_data[field])

    if not assignments:
        return get_task(organization_id, task_id)

    values.extend([task_id, organization_id])

    with database_transaction() as connection:
        cursor = connection.execute(
            f"""
            UPDATE tasks
            SET {", ".join(assignments)}
            WHERE id = ? AND organization_id = ?
            """,
            values,
        )

        if cursor.rowcount == 0:
            return None

    return get_task(organization_id, task_id)

def delete_task(organization_id: int, task_id: int) -> bool:
    with database_transaction() as connection:
        cursor = connection.execute(
            """
            DELETE FROM tasks
            WHERE id = ? AND organization_id = ?
            """,
            (task_id,organization_id),
        )

        return cursor.rowcount > 0

def get_organizations() -> list[dict]:
    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name
            FROM organizations
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def create_organization(name: str) -> dict | None:
    with database_transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO organizations (name)
            VALUES (?)
            ON CONFLICT(name) DO NOTHING
            """,
            (name,),
        )

        if cursor.rowcount == 0:
            return None

        organization_id = cursor.lastrowid

        if organization_id is None:
            raise RuntimeError(
                "SQLite did not return an organization id"
            )

        row = connection.execute(
            """
            SELECT id, name
            FROM organizations
            WHERE id = ?
            """,
            (organization_id,),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "Created organization was not found"
            )

        return dict(row)