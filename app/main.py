"""Luna Guardian REST application and authenticated MCP Streamable HTTP server."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from . import agent, core

current_user: ContextVar[str] = ContextVar("current_user", default="")
current_auth_token: ContextVar[str] = ContextVar("current_auth_token", default="")
current_request_id: ContextVar[str] = ContextVar("current_request_id", default="")


def _token_map() -> dict[str, str]:
    tokens: dict[str, str]
    raw = os.getenv("LUNA_AUTH_TOKENS")
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("LUNA_AUTH_TOKENS must be a JSON object mapping tokens to user IDs") from exc
        if (
            not isinstance(parsed, dict)
            or not parsed
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in parsed.items())
        ):
            raise RuntimeError("LUNA_AUTH_TOKENS must be a non-empty string-to-string JSON object")
        tokens = parsed
    else:
        generated_token = os.getenv("LUNA_AUTH_TOKEN")
        if generated_token:
            tokens = {generated_token: os.getenv("LUNA_AUTH_USER_ID", "demo-student")}
        elif os.getenv("LUNA_ENV", "development") == "production":
            raise RuntimeError("Set LUNA_AUTH_TOKENS or LUNA_AUTH_TOKEN before running in production")
        else:
            tokens = {"demo-token": "demo-student"}
    public_demo_token = os.getenv("LUNA_PUBLIC_DEMO_TOKEN", "").strip()
    if public_demo_token:
        tokens[public_demo_token] = os.getenv("LUNA_PUBLIC_DEMO_USER_ID", "demo-student")
    return tokens


TOKENS = _token_map()
PUBLIC_PATHS = {"/", "/health", "/api/status", "/docs", "/openapi.json", "/favicon.ico"}


class SecurityMiddleware:
    """Bearer authentication plus a small per-token request rate limit."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.limit = int(os.getenv("LUNA_RATE_LIMIT_PER_MINUTE", "120"))

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("path") in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode("latin-1")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        user_id = TOKENS.get(token)
        if not user_id:
            response = JSONResponse(
                {"detail": "Valid Bearer token required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"}
            )
            await response(scope, receive, send)
            return
        now = time.monotonic()
        bucket = self.hits[token]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            response = JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"})
            await response(scope, receive, send)
            return
        bucket.append(now)
        context_token = current_user.set(user_id)
        auth_token = current_auth_token.set(token)
        request_id = headers.get(b"x-luna-request-id", b"").decode("latin-1")[:100]
        request_token = current_request_id.set(request_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_request_id.reset(request_token)
            current_auth_token.reset(auth_token)
            current_user.reset(context_token)


def user() -> str:
    value = current_user.get()
    if not value:
        raise HTTPException(401, "Authentication context unavailable")
    return value


def run_tool(name: str, arguments: dict[str, Any]) -> Any:
    return agent.execute_tool(user(), name, arguments, current_request_id.get() or None)


def _mcp_url() -> str:
    configured = os.getenv("LUNA_MCP_URL")
    if configured:
        return configured.rstrip("/") + "/"
    return f"http://127.0.0.1:{os.getenv('PORT', '8000')}/mcp/"


def _mcp_result_value(result: Any) -> Any:
    if result.isError:
        details = " ".join(getattr(block, "text", "") for block in result.content).strip()
        raise RuntimeError(details or "MCP tool execution failed")
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    if result.structuredContent is not None:
        structured = result.structuredContent
        if isinstance(structured, dict) and set(structured) == {"result"}:
            return structured["result"]
        return structured
    return None


async def _execute_mcp_tool_async(name: str, arguments: dict[str, Any], request_id: str | None) -> Any:
    token = current_auth_token.get()
    if not token:
        raise RuntimeError("Authenticated MCP tool execution requires the caller's bearer token")
    headers = {"Authorization": f"Bearer {token}"}
    if request_id:
        headers["X-Luna-Request-ID"] = request_id
    async with httpx.AsyncClient(headers=headers, timeout=45, follow_redirects=True) as client:
        async with streamable_http_client(_mcp_url(), http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return _mcp_result_value(await session.call_tool(name, arguments))


def execute_mcp_tool(user_id: str, name: str, arguments: dict[str, Any], request_id: str | None = None) -> Any:
    del user_id  # Identity is enforced by the bearer token at the MCP boundary.
    return asyncio.run(_execute_mcp_tool_async(name, arguments, request_id))


def _mcp_transport_security() -> TransportSecuritySettings:
    public_host = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("LUNA_PUBLIC_HOST")
    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*", "testserver"]
    allowed_origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    if public_host:
        allowed_hosts.append(public_host)
        allowed_origins.append(f"https://{public_host}")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


mcp = FastMCP(
    "Luna Guardian",
    host="0.0.0.0",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=_mcp_transport_security(),
)


@mcp.tool()
def create_task(
    title: str, deadline: str, estimated_minutes: int, priority: int = 3, description: str = "", course: str = ""
) -> dict:
    """Create a persistent academic task. Deadline must include a timezone offset."""
    return run_tool("create_task", locals())


@mcp.tool()
def list_tasks(status: str | None = None) -> list[dict]:
    """List the authenticated student's persistent tasks, optionally filtered by status."""
    return run_tool("list_tasks", {"status": status} if status else {})


@mcp.tool()
def update_task(
    task_id: int,
    title: str | None = None,
    deadline: str | None = None,
    estimated_minutes: int | None = None,
    priority: int | None = None,
    description: str | None = None,
    course: str | None = None,
    status: str | None = None,
) -> dict:
    """Update selected fields on a task owned by the authenticated student."""
    return run_tool("update_task", {key: value for key, value in locals().items() if value is not None})


@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Mark a task complete and cancel its remaining planned sessions."""
    return run_tool("complete_task", {"task_id": task_id})


@mcp.tool()
def create_study_plan(start_at: str, available_minutes: int) -> dict:
    """Create and persist a deadline-prioritized plan with focused sessions."""
    return run_tool("create_study_plan", locals())


@mcp.tool()
def get_study_plan(plan_id: int | None = None) -> dict | None:
    """Get the latest or selected persisted study plan."""
    return run_tool("get_study_plan", {"plan_id": plan_id} if plan_id else {})


@mcp.tool()
def replan_missed_session(session_id: int, start_at: str, available_minutes: int) -> dict:
    """Mark a planned session missed and persist a replacement plan."""
    return run_tool("replan_missed_session", locals())


@mcp.tool()
def get_student_context() -> dict:
    """Read persistent preferences and academic commitments."""
    return run_tool("get_student_context", {})


@mcp.tool()
def update_student_context(
    timezone_name: str | None = None, preferences: dict | None = None, commitments: list[dict] | None = None
) -> dict:
    """Persist preferences, commitments, or the student's timezone."""
    return run_tool("update_student_context", {key: value for key, value in locals().items() if value is not None})


@asynccontextmanager
async def lifespan(app: FastAPI):
    with core.connect():
        pass
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Luna Guardian AI", version="0.2.0", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())
app.add_middleware(SecurityMiddleware)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    deadline: str
    estimated_minutes: int = Field(ge=1, le=10080)
    priority: int = Field(default=3, ge=1, le=5)
    description: str = Field(default="", max_length=2000)
    course: str = Field(default="", max_length=100)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    deadline: str | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=10080)
    priority: int | None = Field(default=None, ge=1, le=5)
    description: str | None = Field(default=None, max_length=2000)
    course: str | None = Field(default=None, max_length=100)
    status: str | None = None


class PlanCreate(BaseModel):
    start_at: str
    available_minutes: int = Field(ge=1, le=1440)


class Replan(PlanCreate):
    session_id: int = Field(gt=0)


class AgentMessage(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class StudentContextUpdate(BaseModel):
    timezone_name: str | None = Field(default=None, max_length=100)
    preferences: dict[str, Any] | None = None
    commitments: list[dict[str, Any]] | None = None


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")


@app.get("/health")
@app.get("/api/status")
def health() -> dict:
    status = {
        "status": "ok",
        "service": "luna-guardian",
        "agent_provider": os.getenv("LUNA_AGENT_PROVIDER", "local"),
        "agent_tool_transport": os.getenv("LUNA_AGENT_TOOL_TRANSPORT", "direct"),
    }
    public_demo_token = os.getenv("LUNA_PUBLIC_DEMO_TOKEN", "").strip()
    if public_demo_token:
        status["demo_bearer_token"] = public_demo_token
    return status


@app.get("/api/tasks")
def api_list_tasks(status: str | None = None, user_id: str = Depends(user)) -> list[dict]:
    return core.list_tasks(user_id, status)


@app.post("/api/tasks", status_code=201)
def api_create_task(data: TaskCreate, user_id: str = Depends(user)) -> dict:
    return agent.execute_tool(user_id, "create_task", data.model_dump())


@app.patch("/api/tasks/{task_id}")
def api_update_task(task_id: int, data: TaskUpdate, user_id: str = Depends(user)) -> dict:
    return agent.execute_tool(user_id, "update_task", {"task_id": task_id, **data.model_dump(exclude_none=True)})


@app.post("/api/tasks/{task_id}/complete")
def api_complete_task(task_id: int, user_id: str = Depends(user)) -> dict:
    return agent.execute_tool(user_id, "complete_task", {"task_id": task_id})


@app.post("/api/plans", status_code=201)
def api_create_plan(data: PlanCreate, user_id: str = Depends(user)) -> dict:
    return agent.execute_tool(user_id, "create_study_plan", data.model_dump())


@app.get("/api/plans/current")
def api_get_plan(user_id: str = Depends(user)) -> dict | None:
    return core.get_study_plan(user_id)


@app.post("/api/plans/replan")
def api_replan(data: Replan, user_id: str = Depends(user)) -> dict:
    return agent.execute_tool(user_id, "replan_missed_session", data.model_dump())


@app.get("/api/sessions")
def api_sessions(active_only: bool = True, user_id: str = Depends(user)) -> list[dict]:
    return core.list_sessions(user_id, active_only)


@app.post("/api/sessions/{session_id}/complete")
def api_complete_session(session_id: int, user_id: str = Depends(user)) -> dict:
    result = core.complete_session(user_id, session_id)
    core.log_activity(user_id, "complete_session", {"session_id": session_id}, "success", result, 1)
    return result


@app.get("/api/context")
def api_get_context(user_id: str = Depends(user)) -> dict:
    return core.get_student_context(user_id)


@app.put("/api/context")
def api_update_context(data: StudentContextUpdate, user_id: str = Depends(user)) -> dict:
    return agent.execute_tool(user_id, "update_student_context", data.model_dump(exclude_none=True))


@app.post("/api/agent")
def api_agent(data: AgentMessage, user_id: str = Depends(user)) -> dict:
    try:
        use_mcp = os.getenv("LUNA_AGENT_TOOL_TRANSPORT", "direct").lower() == "mcp"
        result = agent.respond(user_id, data.message, execute_mcp_tool if use_mcp else agent.execute_tool)
        result["tool_transport"] = "mcp" if use_mcp else "direct"
        return result
    except agent.ProviderUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except agent.ProviderRequestError as exc:
        raise HTTPException(502, str(exc)) from exc
    except (RuntimeError, httpx.HTTPError) as exc:  # type: ignore[name-defined]
        raise HTTPException(502, "Luna could not complete that request safely.") from exc


@app.get("/api/activity")
def api_activity(limit: int = 50, user_id: str = Depends(user)) -> list[dict]:
    return core.list_activity(user_id, limit)
