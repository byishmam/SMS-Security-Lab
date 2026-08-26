"""Automated tests for the SMS Security Lab Flask app.

These tests run entirely against Flask's in-process test client and
never touch the network.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import app as app_module


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        with app_module._state_lock:
            app_module.state.clear()
        yield c
        with app_module._state_lock:
            app_module.state.clear()


def test_index_loads(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"SMS Security Lab" in res.data


def test_send_success_or_failure(client):
    res = client.post("/api", json={"number": "8801700000000", "message": "hello"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["event"]["status"] in ("DELIVERED", "FAILED")
    assert data["stats"]["attempts"] == 1


def test_missing_number(client):
    res = client.post("/api", json={"number": "", "message": "hi"})
    assert res.status_code == 400
    assert "recipient" in res.get_json()["error"].lower()


def test_missing_message(client):
    res = client.post("/api", json={"number": "8801700000000", "message": ""})
    assert res.status_code == 400
    assert "message" in res.get_json()["error"].lower()


def test_message_too_long(client):
    res = client.post(
        "/api", json={"number": "8801700000000", "message": "x" * 321}
    )
    assert res.status_code == 400
    assert "320" in res.get_json()["error"]


def test_invalid_number(client):
    res = client.post("/api", json={"number": "not-a-number", "message": "hi"})
    assert res.status_code == 400
    assert "valid-looking phone number" in res.get_json()["error"]


def test_state_endpoint(client):
    client.post("/api", json={"number": "8801700000000", "message": "hi"})
    res = client.get("/api/state")
    data = res.get_json()
    assert "events" in data and "inbox" in data and "stats" in data
    assert len(data["events"]) == 1


def test_clear_endpoint(client):
    client.post("/api", json={"number": "8801700000000", "message": "hi"})
    res = client.post("/api/clear")
    assert res.get_json() == {"ok": True}
    state_res = client.get("/api/state")
    data = state_res.get_json()
    assert data["events"] == []
    assert data["inbox"] == []
    assert data["stats"]["attempts"] == 0


def test_exactly_one_event_per_request(client):
    client.post("/api", json={"number": "8801700000000", "message": "hi"})
    client.post("/api", json={"number": "8801700000001", "message": "hi again"})
    res = client.get("/api/state")
    data = res.get_json()
    assert len(data["events"]) == 2
    assert data["stats"]["attempts"] == 2


def test_successful_delivery_creates_inbox_message(client, monkeypatch):
    # Force success deterministically.
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    res = client.post("/api", json={"number": "8801700000000", "message": "hi"})
    data = res.get_json()
    assert data["event"]["status"] == "DELIVERED"
    assert len(data["inbox"]) == 1


def test_failed_delivery_does_not_create_inbox_message(client, monkeypatch):
    # Force failure deterministically.
    monkeypatch.setattr(app_module.random, "random", lambda: 0.999)
    res = client.post("/api", json={"number": "8801700000000", "message": "hi"})
    data = res.get_json()
    assert data["event"]["status"] == "FAILED"
    assert len(data["inbox"]) == 0
