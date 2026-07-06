"""HTTP integration tests for the arena router."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_client():
    from app.routers.arena import _agents, _agents_by_id, _arena_games, _game_participants
    _agents.clear()
    _agents_by_id.clear()
    _arena_games.clear()
    _game_participants.clear()
    from app.routers.arena import router
    a = FastAPI()
    a.include_router(router, prefix="/api/arena")
    return TestClient(a)


@pytest.fixture
def client():
    return _make_client()


def _register(client, name="testbot"):
    resp = client.post("/api/arena/register", json={
        "name": name,
        "callback_url": "http://example.com",
        "metadata": {"skip_health": True},
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_register_rejects_bad_url(client):
    resp = client.post("/api/arena/register", json={"name": "b", "callback_url": "not-a-url"})
    assert resp.status_code == 400


def test_ok_register(client):
    data = _register(client)
    assert data["agent_id"].startswith("tsa_")
    assert data["api_key"].startswith("tsa_")


def test_protocol_public(client):
    resp = client.get("/api/arena/protocol")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0"


def test_agents_empty(client):
    assert client.get("/api/arena/agents").json() == []


def test_agents_populated(client):
    _register(client, "a")
    _register(client, "b")
    assert len(client.get("/api/arena/agents").json()) == 2


def test_create_game(client):
    a = _register(client)
    resp = client.post("/api/arena/games", json={"name": "g1", "max_players": 10},
                       headers={"Authorization": f"Bearer {a['api_key']}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "g1"


def test_join_leave(client):
    a1 = _register(client)
    a2 = _register(client, "bob")
    h1 = {"Authorization": f"Bearer {a1['api_key']}"}
    h2 = {"Authorization": f"Bearer {a2['api_key']}"}
    game = client.post("/api/arena/games", json={"name": "g", "max_players": 4}, headers=h1).json()

    assert client.post(f"/api/arena/games/{game['game_id']}/join", headers=h2).status_code == 200
    detail = client.get(f"/api/arena/games/{game['game_id']}").json()
    assert detail["registered_count"] == 2
    assert client.post(f"/api/arena/games/{game['game_id']}/leave", headers=h2).status_code == 200


def test_unauth_create(client):
    assert client.post("/api/arena/games", json={"name": "x"}).status_code == 401


def test_bad_token(client):
    resp = client.post("/api/arena/games", json={"name": "x"},
                       headers={"Authorization": "Bearer deadbeefdeadbeef"})
    assert resp.status_code == 401
