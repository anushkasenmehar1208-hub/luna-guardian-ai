import pytest
from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer demo-token"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def test_authentication_is_required(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/health").status_code == 200


def test_natural_language_agent_executes_and_persists_tools(client):
    response = client.post(
        "/api/agent",
        headers=HEADERS,
        json={"message": "I have a Java exam tomorrow, two assignments, and three hours available."},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["provider"] == "local-rules"
    assert [step["tool"] for step in data["steps"]].count("create_task") == 3
    assert data["steps"][-1]["tool"] == "create_study_plan"
    tasks = client.get("/api/tasks", headers=HEADERS).json()
    sessions = client.get("/api/sessions", headers=HEADERS).json()
    activity = client.get("/api/activity", headers=HEADERS).json()
    assert len(tasks) == 3
    assert sessions
    assert any(item["tool_name"] == "create_study_plan" for item in activity)


def test_api_validation_and_task_completion(client):
    bad = client.post("/api/tasks", headers=HEADERS, json={"title": "", "deadline": "bad", "estimated_minutes": 0})
    assert bad.status_code == 422
    created = client.post(
        "/api/tasks",
        headers=HEADERS,
        json={"title": "Essay", "deadline": "2027-01-01T12:00:00+05:30", "estimated_minutes": 60},
    )
    assert created.status_code == 201
    done = client.post(f"/api/tasks/{created.json()['id']}/complete", headers=HEADERS)
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
