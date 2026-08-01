from fastapi.testclient import TestClient
import database
import pytest
import sqlite3


def test_default_organization_created(client: TestClient):
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


def test_tasks_belong_to_default_organization(client: TestClient):
    with database.database_connection() as connection:
        rows = connection.execute("""
            SELECT organization_id
            FROM tasks
            ORDER BY id
            """).fetchall()

    assert [row["organization_id"] for row in rows] == [1, 1]


def test_task_rejects_unknown_organization(client: TestClient):
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


def test_create_organization(client: TestClient):
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


def test_rejects_duplicate_organization_name(client: TestClient):
    response = client.post(
        "/organizations",
        json={"name": "Default Organization"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Organization name already exists",
    }


def test_cannot_access_task_from_another_organization(client: TestClient):
    create_response = client.post(
        "/organizations",
        json={"name": "Second Organization"},
    )

    assert create_response.status_code == 201

    response = client.get("/organizations/2/tasks/1")

    assert response.status_code == 404


def test_get_organization(client: TestClient):
    response = client.get("/organizations/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Default Organization",
    }


def test_get_missing_organization(client: TestClient):
    response = client.get("/organizations/999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Organization not found",
    }


def test_cannot_get_tasks_for_missing_organization(client: TestClient):
    response = client.get("/organizations/999/tasks")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Organization not found",
    }


def test_cannot_create_task_for_missing_organization(client: TestClient):
    response = client.post(
        "/organizations/999/tasks",
        json={
            "title": "Impossible task",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Organization not found",
    }
