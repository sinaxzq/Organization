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
    response = client.patch("/organizations/1/tasks/1", json={
                "status": "done",
            },)
    
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