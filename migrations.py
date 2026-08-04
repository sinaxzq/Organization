import sqlite3

LATEST_SCHEMA_VERSION = 8


def migrate_database(
    connection: sqlite3.Connection,
) -> None:
    version_row = connection.execute("PRAGMA user_version").fetchone()

    if version_row is None:
        raise RuntimeError("SQLite did not return schema version")

    version = version_row[0]

    if version < 1:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
                    CHECK(length(title) BETWEEN 1 AND 200),
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK(
                        status IN (
                            'todo',
                            'in_progress',
                            'done'
                        )
                    )
            )
            """)

        connection.execute("PRAGMA user_version = 1")
        version = 1

    if version < 2:
        connection.execute("""
            CREATE TABLE organizations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
                    CHECK(length(name) BETWEEN 1 AND 200)
            )
            """)

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
        connection.execute("""
            CREATE TABLE tasks_new (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER NOT NULL
                    REFERENCES organizations(id),
                title TEXT NOT NULL
                    CHECK(length(title) BETWEEN 1 AND 200),
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK(
                        status IN (
                            'todo',
                            'in_progress',
                            'done'
                        )
                    )
            )
            """)

        connection.execute("""
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
            """)

        connection.execute("DROP TABLE tasks")

        connection.execute("ALTER TABLE tasks_new RENAME TO tasks")

        connection.execute("""
            CREATE INDEX idx_tasks_organization_id
            ON tasks(organization_id)
            """)

        connection.execute("PRAGMA user_version = 3")

    if version < 4:
        connection.execute("""
            ALTER TABLE tasks
            ADD COLUMN priority INTEGER NOT NULL DEFAULT 0
                CHECK(priority BETWEEN 0 AND 5)
            """)

        connection.execute("PRAGMA user_version = 4")

        version = 4

    if version < 5:
        connection.execute("""
            ALTER TABLE tasks
            ADD COLUMN due_date TEXT
            """)

        connection.execute("PRAGMA user_version = 5")

        version = 5

    if version < 6:
        connection.execute("""
            CREATE TABLE organization_members (
                id INTEGER PRIMARY KEY,
                organization_id INTEGER NOT NULL
                    REFERENCES organizations(id)
                    ON DELETE CASCADE,
                name TEXT NOT NULL
                    CHECK(length(name) BETWEEN 1 AND 200),
                UNIQUE(organization_id, name)
            )
            """)

        connection.execute("PRAGMA user_version = 6")

        version = 6

    if version < 7:
        connection.execute("""
            CREATE UNIQUE INDEX
            idx_organization_members_organization_id_id
            ON organization_members(organization_id, id)
            """)

        connection.execute("""
            CREATE TABLE tasks_new (
                id INTEGER PRIMARY KEY,

                organization_id INTEGER NOT NULL
                    REFERENCES organizations(id),

                title TEXT NOT NULL
                    CHECK(length(title) BETWEEN 1 AND 200),

                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK(
                        status IN (
                            'todo',
                            'in_progress',
                            'done'
                        )
                    ),

                priority INTEGER NOT NULL DEFAULT 0
                    CHECK(priority BETWEEN 0 AND 5),

                due_date TEXT,

                assignee_id INTEGER,

                FOREIGN KEY (
                    organization_id,
                    assignee_id
                )
                REFERENCES organization_members(
                    organization_id,
                    id
                )
            )
            """)

        connection.execute("""
            INSERT INTO tasks_new (
                id,
                organization_id,
                title,
                status,
                priority,
                due_date,
                assignee_id
            )
            SELECT
                id,
                organization_id,
                title,
                status,
                priority,
                due_date,
                NULL
            FROM tasks
            """)

        connection.execute("DROP TABLE tasks")

        connection.execute("ALTER TABLE tasks_new RENAME TO tasks")

        connection.execute("""
            CREATE INDEX idx_tasks_organization_id
            ON tasks(organization_id)
            """)

        connection.execute("""
            CREATE INDEX idx_tasks_assignee
            ON tasks(organization_id, assignee_id)
            """)

        connection.execute("PRAGMA user_version = 7")
        version = 7

    if version < 8:
        connection.execute("""
            DROP INDEX IF EXISTS
            idx_tasks_organization_id
            """)

        connection.execute("PRAGMA user_version = 8")

        version = 8
