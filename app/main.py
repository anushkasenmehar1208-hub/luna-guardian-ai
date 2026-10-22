"""Luna Guardian: working REST UI plus real MCP Streamable HTTP server."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from . import core

mcp = FastMCP('Luna Guardian', stateless_http=True, json_response=True, streamable_http_path='/')

@mcp.tool()
def add_study_task(title: str, deadline: str, minutes: int) -> dict:
    """Create a persistent task. Deadline requires an ISO-8601 timezone offset."""
    return core.create_task(title, deadline, minutes)

@mcp.tool()
def get_study_tasks() -> list[dict]:
    """Retrieve pending and completed tasks from persistent storage."""
    return core.list_tasks()

@mcp.tool()
def generate_study_plan(start_at: str, available_minutes: int) -> dict:
    """Allocate available minutes to upcoming tasks by deadline, 50-minute sessions."""
    return core.build_plan(start_at, available_minutes)

@mcp.tool()
def mark_task_completed(task_id: int) -> dict:
    """Mark a task complete; cancel its planned sessions."""
    return core.complete_task(task_id)

@mcp.tool()
def get_study_sessions() -> list[dict]:
    """Retrieve the current scheduled study sessions."""
    return core.list_sessions()

@asynccontextmanager
async def lifespan(app: FastAPI):
    with core.connect():
        pass
    async with mcp.session_manager.run():
        yield

app = FastAPI(title='Luna Guardian AI', lifespan=lifespan)
app.mount('/mcp', mcp.streamable_http_app())

class Task(BaseModel):
    title: str
    deadline: str
    minutes: int = Field(ge=1, le=1440)

class Plan(BaseModel):
    start_at: str
    available_minutes: int = Field(ge=1, le=1440)

@app.get('/')
def index():
    return FileResponse(Path(__file__).resolve().parent.parent / 'static' / 'index.html')

@app.get('/api/tasks')
def tasks():
    return core.list_tasks()

@app.post('/api/tasks')
def add_task(task: Task):
    try:
        return core.create_task(**task.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

@app.post('/api/tasks/{task_id}/complete')
def finish(task_id: int):
    try:
        return core.complete_task(task_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e

@app.post('/api/plan')
def plan(data: Plan):
    try:
        return core.build_plan(**data.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

@app.get('/api/sessions')
def sessions():
    return core.list_sessions()
