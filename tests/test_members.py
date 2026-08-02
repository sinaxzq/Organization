def test_create_and_list_member(client):
    create_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    assert create_response.status_code == 201
    assert create_response.json() == {
        "id": 1,
        "name": "Alice",
    }

    list_response = client.get("/organizations/1/members")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": 1,
            "name": "Alice",
        }
    ]


def test_rejects_duplicate_member_name(client):
    client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    assert response.status_code == 409


def test_same_member_name_allowed_in_different_organizations(
    client,
):
    client.post(
        "/organizations",
        json={"name": "Second Organization"},
    )

    first_response = client.post(
        "/organizations/1/members",
        json={"name": "Alice"},
    )

    second_response = client.post(
        "/organizations/2/members",
        json={"name": "Alice"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


def test_cannot_create_member_for_missing_organization(
    client,
):
    response = client.post(
        "/organizations/999/members",
        json={"name": "Alice"},
    )

    assert response.status_code == 404
