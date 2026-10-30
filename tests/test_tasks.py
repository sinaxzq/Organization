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


def test_create_task_with_assignee(client):
    member_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    member_id = member_response.json()["id"]

    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Assigned task",
            "assignee_id": member_id,
        },
    )

    assert response.status_code == 201
    assert response.json()["assignee_id"] == member_id


def test_assign_task_to_member(client):
    member_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    member_id = member_response.json()["id"]

    response = client.patch(
        "/organizations/1/tasks/1",
        json={"assignee_id": member_id},
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == member_id


def test_clear_task_assignee(client):
    member_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    member_id = member_response.json()["id"]

    client.patch(
        "/organizations/1/tasks/1",
        json={"assignee_id": member_id},
    )

    response = client.patch(
        "/organizations/1/tasks/1",
        json={"assignee_id": None},
    )

    assert response.status_code == 200
    assert response.json()["assignee_id"] is None


def test_cannot_assign_member_from_another_organization(
    client,
):
    organization_response = client.post(
        "/organizations",
        json={"name": "Second Organization"},
    )

    organization_id = organization_response.json()["id"]

    member_response = client.post(
        f"/organizations/{organization_id}/members",
        json={"name": "Bob"},
    )

    member_id = member_response.json()["id"]

    response = client.patch(
        "/organizations/1/tasks/1",
        json={"assignee_id": member_id},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": ("Assignee does not belong " "to this organization"),
    }


def test_create_task_in_organization_with_assigned_member_from_another_organization(
    client,
):
    organization_response = client.post(
        "/organizations",
        json={"name": "Second Organization"},
    )

    organization_id = organization_response.json()["id"]

    member_response = client.post(
        f"/organizations/{organization_id}/members",
        json={"name": "Bob"},
    )

    member_id = member_response.json()["id"]

    response = client.post(
        "/organizations/1/tasks",
        json={"title": "Test everything", "assignee_id": member_id},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": ("Assignee does not belong " "to this organization"),
    }


def test_filter_tasks_by_assignee(client):
    member_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    member_id = member_response.json()["id"]

    assigned_response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Alice task",
            "assignee_id": member_id,
        },
    )

    client.post(
        "/organizations/1/tasks",
        json={"title": "Unassigned task"},
    )

    response = client.get(
        "/organizations/1/tasks",
        params={"assignee_id": member_id},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == (assigned_response.json()["id"])


def test_get_tasks_for_missing_organization(client):
    response = client.get("/organizations/999/tasks")

    assert response.status_code == 404


def test_get_tasks_due_before(client):
    task_response = client.post(
        "/organizations/1/tasks",
        json={"title": "Task due some date", "due_date": "2026-11-20"},
    )

    response = client.get(
        "/organizations/1/tasks",
        params={"due_before": "2026-11-21"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == (task_response.json()["id"])


def test_due_before_excludes_equal_later_and_null_dates(client):
    dates = [
        "2026-11-19",
        "2026-11-20",
        "2026-11-21",
        None,
    ]

    task_ids = []

    for due_date in dates:
        response = client.post(
            "/organizations/1/tasks",
            json={
                "title": f"Task with date {due_date}",
                "due_date": due_date,
            },
        )
        assert response.status_code == 201
        task_ids.append(response.json()["id"])

    response = client.get(
        "/organizations/1/tasks",
        params={"due_before": "2026-11-20"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["count"] == 1
    assert [task["id"] for task in body["items"]] == [task_ids[0]]


@pytest.mark.parametrize(
    "invalid_date",
    [
        "invalid",
        "2026-02-30",
        "2026-13-01",
        "",
    ],
)
def test_due_before_rejects_invalid_date(client, invalid_date):
    response = client.get(
        "/organizations/1/tasks",
        params={"due_before": invalid_date},
    )

    assert response.status_code == 422


def test_due_before_combines_with_filters_and_pagination(client):
    member_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )
    assert member_response.status_code == 201

    member_id = member_response.json()["id"]

    base_task = {
        "status": "todo",
        "priority": 5,
        "due_date": "2026-11-19",
        "assignee_id": member_id,
    }

    matching_ids = []

    for title in ("Release A", "Release B"):
        response = client.post(
            "/organizations/1/tasks",
            json={**base_task, "title": title},
        )
        assert response.status_code == 201
        matching_ids.append(response.json()["id"])

    non_matching_tasks = [
        {"title": "Release done", "status": "done"},
        {"title": "Release low priority", "priority": 4},
        {"title": "Other task"},
        {"title": "Release unassigned", "assignee_id": None},
    ]

    for task in non_matching_tasks:
        response = client.post(
            "/organizations/1/tasks",
            json={**base_task, **task},
        )
        assert response.status_code == 201

    response = client.get(
        "/organizations/1/tasks",
        params={
            "due_before": "2026-11-20",
            "status": "todo",
            "priority": 5,
            "assignee_id": member_id,
            "q": "release",
            "sort": "priority_desc",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 2
    assert body["count"] == 1
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert [task["id"] for task in body["items"]] == [matching_ids[1]]


def test_tasks_without_due_before_preserve_previous_behavior(client):
    response = client.post(
        "/organizations/1/tasks",
        json={
            "title": "Task with deadline",
            "due_date": "2026-11-20",
        },
    )
    assert response.status_code == 201

    created_id = response.json()["id"]

    response = client.get("/organizations/1/tasks")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["count"] == 3
    assert [task["id"] for task in body["items"]] == [
        1,
        2,
        created_id,
    ]


@pytest.mark.parametrize(
    "sort, expected_dates",
    [
        (
            "due_date_asc",
            [None, None, None, "2026-11-10", "2026-11-20", "2026-11-30"],
        ),
        (
            "due_date_desc",
            ["2026-11-30", "2026-11-20", "2026-11-10", None, None, None],
        ),
    ],
)
def test_sort_tasks_by_due_date(client, sort, expected_dates):
    for due_date in ("2026-11-30", "2026-11-10", "2026-11-20", None):
        response = client.post(
            "/organizations/1/tasks",
            json={
                "title": f"Task {due_date}",
                "due_date": due_date,
            },
        )
        assert response.status_code == 201

    response = client.get(
        "/organizations/1/tasks",
        params={"sort": sort},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 6
    assert body["count"] == 6
    assert [task["due_date"] for task in body["items"]] == expected_dates


@pytest.mark.parametrize(
    "sort, expected_order",
    [
        ("due_date_asc", [0, 1, 2]),
        ("due_date_desc", [2, 0, 1]),
    ],
)
def test_sort_due_date_uses_id_as_tiebreaker(client, sort, expected_order):
    dates = [
        "2026-11-20",
        "2026-11-20",
        "2026-11-30",
    ]

    created_ids = []

    for index, due_date in enumerate(dates):
        response = client.post(
            "/organizations/1/tasks",
            json={
                "title": f"Task {index}",
                "due_date": due_date,
            },
        )
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    response = client.get(
        "/organizations/1/tasks",
        params={
            "sort": sort,
            "due_before": "2026-12-01",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert [task["id"] for task in body["items"]] == [
        created_ids[index] for index in expected_order
    ]


@pytest.mark.parametrize(
    "sort, expected_dates",
    [
        ("due_date_asc", ["2026-11-20", "2026-11-25"]),
        ("due_date_desc", ["2026-11-25", "2026-11-20"]),
    ],
)
def test_due_date_sort_with_pagination(client, sort, expected_dates):
    for due_date in (
        "2026-11-30",
        "2026-11-10",
        "2026-11-20",
        "2026-11-25",
    ):
        response = client.post(
            "/organizations/1/tasks",
            json={
                "title": f"Task {due_date}",
                "due_date": due_date,
            },
        )
        assert response.status_code == 201

    response = client.get(
        "/organizations/1/tasks",
        params={
            "sort": sort,
            "due_before": "2026-12-01",
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 4
    assert body["count"] == 2
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [task["due_date"] for task in body["items"]] == expected_dates


def test_task_duplicate_with_same_organization_and_user(client):
    org_response = client.post("/organizations", json={"name": "TestOrg"})

    org_id = org_response.json()["id"]

    member_response = client.post(
        f"/organizations/{org_id}/members",
        json={"name": "TestMember"},
    )

    task_response = client.post(
        "/organizations/1/tasks/",
        json={"title": "Test task", "assignee_id": member_response.json()["id"]},
    )

    assert task_response.status_code == 422
