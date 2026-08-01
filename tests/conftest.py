from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import database
from main import app


@pytest.fixture(autouse=True)
def use_test_database(
    tmp_path,
    monkeypatch,
):
    test_database_path = tmp_path / "operations-test.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database_path,
    )

    database.init_database()

    with database.database_transaction() as connection:
        connection.executemany(
            """
            INSERT INTO tasks (
                id,
                organization_id,
                title,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (1, 1, "Настроить backend", "done"),
                (2, 1, "Создать endpoint задач", "todo"),
            ],
        )


@pytest.fixture
def client(
    use_test_database,
) -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
