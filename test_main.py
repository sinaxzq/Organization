from fastapi.testclient import TestClient
import database
from main import app
import pytest
import sqlite3

client = TestClient(app)

@pytest.fixture(autouse=True)
def use_test_database(tmp_path, monkeypatch):
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

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_existing_task():
    response = client.get("/organizations/1/tasks/1")

    assert response.status_code == 200

    task = response.json()

    assert task["id"] == 1
    assert "title" in task
    assert "status" in task


def test_get_missing_task():
    response = client.get("/organizations/1/tasks/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_rejects_invalid_status_filter():
    response = client.get("/organizations/1/tasks?status=potato")

    assert response.status_code == 422

def test_create_task():
    response = client.post(
        "/organizations/1/tasks", 
        json={
            "title": "Написать автоматические тесты",
            "status": "todo",
        },
    )

    assert response.status_code == 201

    created_task = response.json()

    assert isinstance(created_task["id"], int)
    assert created_task["title"] == "Написать автоматические тесты"
    assert created_task["status"] == "todo"

    get_response = client.get(f"/organizations/1/tasks/{created_task['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created_task

def test_update_task():
    response = client.patch("/organizations/1/tasks/1", json={
                "status": "done",
            },)
    
    assert response.status_code == 200

    updated_task = response.json()

    assert updated_task["id"] == 1
    assert updated_task["status"] == "done"
    assert updated_task["title"] == "Настроить backend"

def test_delete_task():
    response = client.delete("/organizations/1/tasks/1")

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get("/organizations/1/tasks/1")

    assert get_response.status_code == 404

def test_database_transaction_rolls_back():
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

def test_search_tasks_is_case_insensitive():
    response = client.get(
        "/organizations/1/tasks",
        params={"q": "НАСТРОИТЬ"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Настроить backend"

def test_tasks_pagination():
    response = client.get(
        "/organizations/1/tasks",
        params={
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert body["items"][0]["id"] == 2

def test_database_schema_version():
    with database.database_connection() as connection:
        row = connection.execute(
            "PRAGMA user_version"
        ).fetchone()

    assert row[0] == 3

def test_default_organization_created():
    with database.database_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name
            FROM organizations
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

    assert row is not None
    assert dict(row) == {
        "id": 1,
        "name": "Default Organization",
    }

def test_tasks_belong_to_default_organization():
    with database.database_connection() as connection:
        rows = connection.execute(
            """
            SELECT organization_id
            FROM tasks
            ORDER BY id
            """
        ).fetchall()

    assert [row["organization_id"] for row in rows] == [1, 1]

def test_task_rejects_unknown_organization():
    with pytest.raises(sqlite3.IntegrityError):
        with database.database_transaction() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    organization_id,
                    title,
                    status
                )
                VALUES (?, ?, ?)
                """,
                (999, "Некорректная задача", "todo"),
            )

def test_create_organization():
    response = client.post(
        "/organizations",
        json={"name": "Acme"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 2,
        "name": "Acme",
    }

    list_response = client.get("/organizations")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": 1,
            "name": "Default Organization",
        },
        {
            "id": 2,
            "name": "Acme",
        },
    ]


def test_rejects_duplicate_organization_name():
    response = client.post(
        "/organizations",
        json={"name": "Default Organization"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Organization name already exists",
    }

def test_cannot_access_task_from_another_organization():
    create_response = client.post(
        "/organizations",
        json={"name": "Second Organization"},
    )

    assert create_response.status_code == 201

    response = client.get(
        "/organizations/2/tasks/1"
    )

    assert response.status_code == 404