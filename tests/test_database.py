from fastapi.testclient import TestClient
import sqlite3
import pytest
import database

def test_database_transaction_rolls_back(client: TestClient):
    with pytest.raises(sqlite3.IntegrityError):
        with database.database_transaction() as connection:
            connection.execute(
                """
                INSERT INTO tasks (title, status)
                VALUES (?, ?)
                """,
                ("Эта задача должна откатиться", "todo"),
            )

            connection.execute(
                """
                INSERT INTO tasks (title, status)
                VALUES (?, ?)
                """,
                ("Некорректная задача", "potato"),
            )

    stored_tasks = database.get_tasks(1)

    assert len(stored_tasks) == 2



def test_database_schema_version(client: TestClient):
    with database.database_connection() as connection:
        row = connection.execute(
            "PRAGMA user_version"
        ).fetchone()

    assert row[0] == 3