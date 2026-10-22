# Luna Guardian AI

Luna Guardian is a voice-first academic planning agent for university students. It turns natural-language commitments into persistent tasks and realistic study sessions, then replans when life interrupts the schedule.

This repository is an **Alexa+-style simulated experience** for the Build, Ship, Shape: Amazon Developer Hackathon 2026. It is not an official Alexa+ integration.

## What is working

- An authenticated MCP server using the official Python SDK, Streamable HTTP, and protocol `2025-11-25`
- Nine persistent tools: `create_task`, `list_tasks`, `update_task`, `complete_task`, `create_study_plan`, `get_study_plan`, `replan_missed_session`, `get_student_context`, and `update_student_context`
- User-isolated SQLite data for context, commitments, tasks, plans, study sessions, completion history, and agent activity
- A tool-calling agent with Amazon Bedrock, OpenAI-compatible, and clearly labelled offline rule-based providers
- A responsive dashboard with live priorities, deadlines, schedule, progress, tool activity, browser speech recognition, text fallback, and optional speech output
- Bearer authentication, bounded request sizes, validation, rate limiting, safe timezone conversion, and database error propagation

## Architecture

```text
Browser voice/text
      │
      ▼
FastAPI /api/agent ──► provider (Bedrock / OpenAI-compatible / local rules)
      │                              │
      └──────── real tool calls ◄────┘
                     │
                     ▼
              domain service ──► SQLite
                     ▲
                     │
MCP client ── Streamable HTTP /mcp/ ── bearer auth
```

The REST simulator and MCP server call the same domain functions. The activity timeline is derived from persisted execution records; it is not fabricated UI state.

## Local setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The development fallback bearer token is `demo-token`. Production refuses to start without `LUNA_AUTH_TOKENS`.

### Configuration

| Variable | Purpose |
|---|---|
| `LUNA_ENV` | `development` or `production` |
| `LUNA_AUTH_TOKENS` | JSON object mapping opaque bearer tokens to stable user IDs |
| `LUNA_DB_PATH` | SQLite database path; use persistent storage in production |
| `LUNA_RATE_LIMIT_PER_MINUTE` | Per-token request limit, default `120` |
| `LUNA_AGENT_PROVIDER` | `local`, `bedrock`, or `openai-compatible` |
| `AWS_REGION` | Bedrock region |
| `LUNA_BEDROCK_MODEL` | Bedrock Converse model ID |
| `LUNA_OPENAI_BASE_URL` | OpenAI-compatible `/v1` base URL |
| `LUNA_OPENAI_MODEL` | Chat-completions model name |
| `LUNA_OPENAI_API_KEY` | Provider key; never commit this value |

The `local` provider is deterministic and useful for an offline demo, but it is not presented as an LLM. Use `bedrock` or `openai-compatible` for the LLM-powered submission demo.

### Amazon Bedrock

```bash
pip install -r requirements-aws.txt
export LUNA_AGENT_PROVIDER=bedrock
export AWS_REGION=us-east-1
export LUNA_BEDROCK_MODEL=amazon.nova-lite-v1:0
uvicorn app.main:app
```

The current development machine had no AWS CLI or visible AWS credentials, so Bedrock has not been live-verified and AWS Builder eligibility is not claimed.

## MCP protocol

Endpoint: `http://127.0.0.1:8000/mcp/`

Every request requires `Authorization: Bearer <token>`. The verified SDK negotiated MCP `2025-11-25`. A genuine official MCP client completed initialization, `tools/list`, `tools/call create_task`, and `tools/call list_tasks` against the running server.

Example client:

```python
import asyncio, httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with httpx.AsyncClient(headers={"Authorization": "Bearer demo-token"}) as http:
        async with streamable_http_client("http://127.0.0.1:8000/mcp/", http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                print((await session.initialize()).protocolVersion)
                print([tool.name for tool in (await session.list_tools()).tools])

asyncio.run(main())
```

REST API documentation is available at `/docs`; the machine-readable OpenAPI contract is `/openapi.json`.

## Verification

```bash
pytest -q
ruff check app tests
python -m compileall -q app tests
```

Verified locally on October 22, 2026:

- 7 automated tests passed
- Ruff passed
- Python compilation passed
- Real MCP initialization negotiated `2025-11-25`
- All nine required tools were discovered
- Authenticated MCP `create_task` and `list_tasks` calls succeeded and persisted data

Browser speech recognition depends on browser support and microphone permission. Chromium-based browsers generally expose the Web Speech API; unsupported or denied cases retain full text input. This is not Alexa voice transport.

## Deployment

The included `Dockerfile` and `render.yaml` run the application on Render with a persistent disk. Before deployment:

1. Generate a long random token.
2. Set `LUNA_AUTH_TOKENS` as a secret JSON object such as `{"token":"student-1"}`.
3. Mount persistent storage at `/var/data`; the blueprint sets `LUNA_DB_PATH=/var/data/luna.db`.
4. Configure an LLM provider and its credentials.
5. Verify `/health`, load the dashboard, and repeat the official MCP client check against HTTPS.

No public deployment or public repository is claimed until its URL is verified.

## Project materials

- [Demo script](docs/demo-script.md)
- [Devpost project story](docs/devpost-story.md)
- [Amazon developer product feedback](docs/amazon-feedback.md)
- [Development friction log](docs/friction-log.md)
- [Security notes](SECURITY.md)

## License

MIT — see [LICENSE](LICENSE).
