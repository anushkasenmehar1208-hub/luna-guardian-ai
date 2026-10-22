# Luna Guardian AI 🌙

An **initial working prototype** for the Alexa+ track of Build, Ship, Shape: Amazon Developer Hackathon 2026.

- Persistent SQLite task management
- Deadline-prioritized study planning and replanning
- Real MCP tools exposed through **Streamable HTTP** using the official Python MCP SDK
- Responsive web simulator with task and planning flows

## Run

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ for the simulator. MCP endpoint: `http://127.0.0.1:8000/mcp`.

The SDK's default protocol negotiation supports current MCP versions; verify the actual negotiated version is **2025-11-25 or later** before submission. The demo must show an MCP client actually calling tools, not merely a REST web UI.

## MCP tools

- `add_study_task(title, deadline, minutes)`
- `get_study_tasks()`
- `generate_study_plan(start_at, available_minutes)`
- `mark_task_completed(task_id)`
- `get_study_sessions()`

Dates use ISO-8601 strings **with timezone offsets**. The scheduler uses earliest deadline first, not an LLM. There is currently no voice input, authentication, calendar integration, or proactive notification system.

## Tests

```bash
pytest -q
```

## Hackathon requirements remaining

- [ ] Verify protocol version and demonstrate tool invocation through a genuine MCP client.
- [ ] Add a voice-first agent client (or clearly identify this as an Alexa+ simulated experience).
- [ ] Add safe multi-user authentication before public deployment.
- [ ] Add product feedback and friction logs.
- [ ] Add additional qualifying open-source contribution if entering that mini challenge.
- [ ] Record public English demo under 3 minutes.
- [ ] Create a public GitHub repo with license and setup instructions.
- [ ] Submit on Devpost before deadline.

## Scope and limitations

This prototype runs locally with one user. It is **not** connected to an actual Alexa+ account, is **not** yet production-ready, and does not claim to have won or entered the hackathon.
