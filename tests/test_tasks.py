from fastapi.testclient import TestClient
import pytest


def test_get_existing_task(client: TestClient):
    response = client.get("/organizations/1/tasks/1")

    assert response.status_code == 200

    task = response.json()

    assert task["id"] == 1
    assert "title" in task
    assert "status" in task


def test_get_missing_task(client: TestClient):
    response = client.get("/organizations/1/tasks/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_rejects_invalid_status_filter(client: TestClient):
    response = client.get("/organizations/1/tasks?status=potato")

    assert response.status_code == 422


def test_create_task(client: TestClient):
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


def test_update_task(client: TestClient):
    response = client.patch(
        "/organizations/1/tasks/1",
        json={
            "status": "done",
        },
    )

    assert response.status_code == 200

    updated_task = response.json()

    assert updated_task["id"] == 1
    assert updated_task["status"] == "done"
    assert updated_task["title"] == "Настроить backend"


def test_delete_task(client: TestClient):
    response = client.delete("/organizations/1/tasks/1")

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get("/organizations/1/tasks/1")

    assert get_response.status_code == 404


def test_search_tasks_is_case_insensitive(client: TestClient):
    response = client.get(
        "/organizations/1/tasks",
        params={"q": "НАСТРОИТЬ"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 1
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Настроить backend"


def test_tasks_pagination(client: TestClient):
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


@pytest.mark.parametrize(
    "payload",
    [
        {"title": None},
        {"status": None},
    ],
)
def test_update_rejects_null_fields(
    client,
    payload,
):
    response = client.patch(
        "/organizations/1/tasks/1",
        json=payload,
    )

    assert response.status_code == 422


def test_create_task_rejects_blank_title(client):
    response = client.post(
        "/organizations/1/tasks",
        json={"title": "   "},
    )

    assert response.status_code == 422


def test_update_task_rejects_blank_title(client):
    response = client.patch(
        "/organizations/1/tasks/1",
        json={"title": "   "},
    )

    assert response.status_code == 422


def test_create_task_strips_title(client):
    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "   Prepare release   ",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Prepare release"


def test_create_task_has_default_priority(client):
    response = client.post(
        "/organizations/1/tasks",
        json={"title": "Default priority"},
    )

    assert response.status_code == 201
    assert response.json()["priority"] == 0


def test_create_task_with_priority(client):
    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Important task",
            "priority": 5,
        },
    )

    assert response.status_code == 201
    assert response.json()["priority"] == 5


@pytest.mark.parametrize(
    "priority",
    [-1, 6],
)
def test_rejects_invalid_task_priority(
    client,
    priority,
):
    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Invalid priority",
            "priority": priority,
        },
    )

    assert response.status_code == 422


def test_filter_tasks_by_priority(client):
    client.post(
        "/organizations/1/tasks",
        json={
            "title": "Important",
            "priority": 5,
        },
    )

    response = client.get(
        "/organizations/1/tasks",
        params={"priority": 5},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["priority"] == 5


def test_sort_tasks_by_priority_desc(client):
    client.post(
        "/organizations/1/tasks",
        json={
            "title": "Important",
            "priority": 5,
        },
    )

    response = client.get(
        "/organizations/1/tasks",
        params={"sort": "priority_desc"},
    )

    priorities = [task["priority"] for task in response.json()["items"]]

    assert priorities == sorted(
        priorities,
        reverse=True,
    )


def test_rejects_unknown_task_sort(client):
    response = client.get(
        "/organizations/1/tasks",
        params={"sort": "DROP TABLE tasks"},
    )

    assert response.status_code == 422


def test_create_task_has_no_due_date_by_default(client):
    response = client.post(
        "/organizations/1/tasks",
        json={"title": "No deadline"},
    )

    assert response.status_code == 201
    assert response.json()["due_date"] is None


def test_create_task_with_due_date(client):
    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Release",
            "due_date": "2026-08-15",
        },
    )

    assert response.status_code == 201
    assert response.json()["due_date"] == "2026-08-15"


def test_rejects_invalid_due_date(client):
    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Impossible deadline",
            "due_date": "2026-02-30",
        },
    )

    assert response.status_code == 422


def test_update_task_due_date(client):
    response = client.patch(
        "/organizations/1/tasks/1",
        json={"due_date": "2026-08-20"},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] == "2026-08-20"


def test_clear_task_due_date(client):
    client.patch(
        "/organizations/1/tasks/1",
        json={"due_date": "2026-08-20"},
    )

    response = client.patch(
        "/organizations/1/tasks/1",
        json={"due_date": None},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is None
