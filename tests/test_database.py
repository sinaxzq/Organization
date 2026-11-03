from fastapi.testclient import TestClient
import sqlite3
import pytest
import database


def test_database_transaction_rolls_back(client: TestClient):
    with pytest.raises(sqlite3.IntegrityError):
        with database.database_transaction() as connection:
            connection.execute(
                """
                INSERT INTO tasks (title, status, organization_id, priority)
                VALUES (?, ?, ?, ?)
                """,
                ("Эта задача должна откатиться", "todo", 1, 0),
            )

            stored_tasks_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM tasks
                WHERE organization_id = ?
                """,
                (1,),
            ).fetchone()[0]

            assert stored_tasks_count == 3

            connection.execute(
                """
                INSERT INTO tasks (title, status, organization_id, priority)
                VALUES (?, ?, ?, ?)
                """,
                ("Некорректная задача", "potato", 999, 666),
            )

    stored_tasks = database.get_tasks(1)[0]

    assert len(stored_tasks) == 2


def test_database_schema_version(client: TestClient):
    with database.database_connection() as connection:
        row = connection.execute("PRAGMA user_version").fetchone()

    assert row[0] == 9


def test_database_rejects_cross_organization_assignee():
    with database.database_transaction() as connection:
        connection.execute(
            """
            INSERT INTO organizations (id, name)
            VALUES (?, ?)
            """,
            (2, "Second Organization"),
        )

        cursor = connection.execute(
            """
            INSERT INTO organization_members (
                organization_id,
                name
            )
            VALUES (?, ?)
            """,
            (2, "Bob"),
        )

        member_id = cursor.lastrowid

    with pytest.raises(sqlite3.IntegrityError):
        with database.database_transaction() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET assignee_id = ?
                WHERE id = ?
                  AND organization_id = ?
                """,
                (
                    member_id,
                    1,
                    1,
                ),
            )


def test_task_indexes():
    with database.database_connection() as connection:
        rows = connection.execute("PRAGMA index_list('tasks')").fetchall()

    index_names = {row["name"] for row in rows}

    assert "idx_tasks_assignee" in index_names
    assert "idx_tasks_organization_id" not in index_names


def test_member_duplicate_with_same_organization_and_user_id(client):
    organization_response = client.post(
        "/organizations",
        json={"name": "TestOrg"},
    )

    assert organization_response.status_code == 201
    organization_id = organization_response.json()["id"]

    with database.database_transaction() as connection:
        user_id = connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            """,
            ("testuser", "test_hash"),
        ).lastrowid

        connection.execute(
            """
            INSERT INTO organization_members (
                organization_id,
                user_id,
                name
            )
            VALUES (?, ?, ?)
            """,
            (organization_id, user_id, "Alice"),
        )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
        with database.database_transaction() as connection:
            connection.execute(
                """
                INSERT INTO organization_members (
                    organization_id,
                    user_id,
                    name
                )
                VALUES (?, ?, ?)
                """,
                (organization_id, user_id, "Bob"),
            )
