import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import agent, main
from app.main import app

HEADERS = {"Authorization": "Bearer demo-token"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as value:
        yield value


def test_authentication_is_required(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/health").status_code == 200
    status = client.get("/api/status")
    assert status.status_code == 200
    assert status.json()["status"] == "ok"


def test_single_generated_token_configuration(monkeypatch):
    monkeypatch.delenv("LUNA_AUTH_TOKENS", raising=False)
    monkeypatch.setenv("LUNA_AUTH_TOKEN", "generated-secret")
    monkeypatch.setenv("LUNA_AUTH_USER_ID", "render-student")
    assert main._token_map() == {"generated-secret": "render-student"}


def test_render_hostname_is_allowed_for_mcp(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "luna-guardian-ai.onrender.com")
    security = main._mcp_transport_security()
    assert security.enable_dns_rebinding_protection is True
    assert "luna-guardian-ai.onrender.com" in security.allowed_hosts
    assert "https://luna-guardian-ai.onrender.com" in security.allowed_origins


def test_natural_language_agent_executes_and_persists_tools(client):
    response = client.post(
        "/api/agent",
        headers=HEADERS,
        json={"message": "I have a Java exam tomorrow, two assignments, and three hours available."},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["provider"] == "local-rules"
    assert data["tool_transport"] == "direct"
    assert [step["tool"] for step in data["steps"]].count("create_task") == 3
    assert data["steps"][-1]["tool"] == "create_study_plan"
    tasks = client.get("/api/tasks", headers=HEADERS).json()
    sessions = client.get("/api/sessions", headers=HEADERS).json()
    activity = client.get("/api/activity", headers=HEADERS).json()
    assert len(tasks) == 3
    assert sessions
    assert any(item["tool_name"] == "create_study_plan" for item in activity)
    assert all(item["request_id"] == data["request_id"] for item in activity[:4])


def test_openai_provider_chooses_tools_through_injected_executor(monkeypatch):
    monkeypatch.setenv("LUNA_OPENAI_API_KEY", "test-key")
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-task",
                                "type": "function",
                                "function": {
                                    "name": "create_task",
                                    "arguments": json.dumps(
                                        {
                                            "title": "Java exam revision",
                                            "deadline": "2026-10-23T23:59:00+05:30",
                                            "estimated_minutes": 120,
                                            "priority": 5,
                                        }
                                    ),
                                },
                            },
                            {
                                "id": "call-plan",
                                "type": "function",
                                "function": {
                                    "name": "create_study_plan",
                                    "arguments": json.dumps(
                                        {
                                            "start_at": "2026-10-22T18:00:00+05:30",
                                            "available_minutes": 120,
                                        }
                                    ),
                                },
                            },
                        ],
                    }
                }
            ]
        },
        {"choices": [{"message": {"role": "assistant", "content": "Your revision plan is ready."}}]},
    ]

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.requests = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):
            self.requests.append((url, kwargs))
            return FakeResponse(responses.pop(0))

    monkeypatch.setattr(agent.httpx, "Client", FakeClient)
    calls = []

    def execute(user_id, name, arguments, request_id):
        calls.append((user_id, name, arguments, request_id))
        if name == "create_task":
            return {"id": 41, **arguments, "status": "pending"}
        return {"plan_id": 7, "sessions": [{"id": 9, "minutes": 120}]}

    result = agent._run_openai("student", "Create my Java revision plan", "req-1", execute)

    assert result["provider"] == "openai-compatible"
    assert result["message"] == "Your revision plan is ready."
    assert [call[1] for call in calls] == ["create_task", "create_study_plan"]
    assert all(call[3] == "req-1" for call in calls)
    assert [step["status"] for step in result["steps"]] == ["success", "success"]


def test_exact_exam_request_does_not_claim_assignment_assumptions(monkeypatch):
    calls = []

    def execute(user_id, name, arguments, request_id):
        calls.append(name)
        if name == "create_task":
            return {"id": 1, **arguments, "status": "pending"}
        return {"plan_id": 2, "sessions": [{"id": 1}, {"id": 2}, {"id": 3}]}

    result = agent._run_local(
        "student",
        "I have a Java exam tomorrow. Create a revision task and schedule two hours of study.",
        "req-exact",
        execute,
    )

    assert calls == ["create_task", "create_study_plan"]
    assert "assignment" not in result["message"].lower()


def test_mcp_result_payload_is_decoded():
    result = SimpleNamespace(
        isError=False,
        content=[SimpleNamespace(text='{"plan_id": 7, "sessions": []}')],
        structuredContent=None,
    )
    assert main._mcp_result_value(result) == {"plan_id": 7, "sessions": []}


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
