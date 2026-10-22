# Devpost project story

## Inspiration

University deadlines rarely arrive one at a time. Students juggle exams, assignments, classes, and limited energy, then lose confidence when a rigid plan breaks. We wanted an assistant that does more than suggest productivity tips: it should execute planning actions, remember them, and adapt when reality changes.

## What it does

Luna Guardian accepts a spoken or typed request, extracts academic commitments, saves prioritized tasks, and creates a focused study schedule around the time available. The student can inspect deadlines, complete tasks, report a missed session, and receive a persisted replacement plan. Every agent action appears in an auditable activity timeline.

## How we built it

The application combines FastAPI, the official Python MCP SDK, PostgreSQL, Pydantic, and a responsive browser dashboard. The live `gemini-3.5-flash-lite` agent uses Google's OpenAI-compatible API and sends authenticated Streamable HTTP requests to the same MCP endpoint available to external clients; the MCP tools and REST dashboard share one persistence layer. The original exact create-and-plan workflow was verified with `gemini-3.1-flash-lite`, and the current model was separately verified selecting and executing `list_tasks` through MCP. Provider adapters also support Amazon Bedrock Converse tool use, while an explicitly labelled deterministic provider keeps local development usable without credentials. Bedrock is not claimed as a verified live integration.

The scheduler prioritizes urgent, high-priority tasks, divides work into sessions of up to 50 minutes, inserts recovery breaks, prevents scheduling after a deadline, and persists every plan. Authentication maps opaque bearer tokens to user identities so database queries remain isolated.

## Challenges

The starter tests did not import in a clean environment, and the original five tools did not match the required contract. The MCP session manager also exposed a lifecycle constraint during repeated in-process tests. We preserved the baseline, introduced a stable contract, isolated the persistence layer, and then tested the real server with the official MCP client.

Voice support also varies between browsers, so the interface exposes permission failures clearly and always retains text input.

## Accomplishments

- Negotiated MCP protocol 2025-11-25 over real Streamable HTTP
- Discovered and executed all nine required persistent tools
- Verified the exact public Java-exam workflow from Gemini tool selection through MCP calls, PostgreSQL rows, dashboard refresh, and activity-ledger evidence
- Built an honest activity ledger tied to actual database operations
- Added user isolation, validation, rate limiting, timezone-safe scheduling, and graceful tool failures
- Passed automated domain and API scenarios for creation, planning, completion, persistence, and replanning
- Delivered a polished voice-first dashboard without claiming official Alexa+ connectivity

## What we learned

Agent transparency is strongest when it comes from the execution boundary rather than model narration. A shared tool dispatcher made both MCP calls and LLM calls record the same evidence. We also learned to treat voice as progressive enhancement and to keep protocol verification separate from ordinary endpoint tests.

## What is next

We would verify Bedrock in an AWS account, add OAuth/OIDC for self-service users, connect a university calendar, add notification preferences, and validate plan quality with students. Official Alexa+ device integration would be pursued only through documented, available interfaces and tested hardware or accounts.
