"""Testy endpointów serii."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_series(client: AsyncClient, auth_headers):
    response = await client.post(
        "/api/v1/series",
        headers=auth_headers,
        json={
            "title": "Finanse osobiste",
            "topic": "Porady dotyczące oszczędzania pieniędzy",
            "language": "pl",
            "tone": "edukacyjny",
            "target_duration_seconds": 60,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Finanse osobiste"
    assert data["topic"] == "Porady dotyczące oszczędzania pieniędzy"
    assert data["is_active"] is True
    assert data["total_episodes"] == 0


@pytest.mark.asyncio
async def test_list_series(client: AsyncClient, auth_headers):
    # Utwórz serię
    await client.post(
        "/api/v1/series",
        headers=auth_headers,
        json={"title": "Test", "topic": "Test topic"},
    )

    response = await client.get("/api/v1/series", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_update_series(client: AsyncClient, auth_headers):
    # Utwórz
    create_resp = await client.post(
        "/api/v1/series",
        headers=auth_headers,
        json={"title": "Old Title", "topic": "Topic"},
    )
    series_id = create_resp.json()["id"]

    # Aktualizuj
    response = await client.patch(
        f"/api/v1/series/{series_id}",
        headers=auth_headers,
        json={"title": "New Title"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_series(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/series",
        headers=auth_headers,
        json={"title": "To Delete", "topic": "Topic"},
    )
    series_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/series/{series_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    # Nie powinno być widoczne na liście
    list_resp = await client.get("/api/v1/series", headers=auth_headers)
    ids = [s["id"] for s in list_resp.json()["items"]]
    assert series_id not in ids
