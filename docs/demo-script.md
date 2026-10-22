# Luna Guardian demo script (under 3 minutes)

**0:00–0:15 — Open on the live dashboard**

“Students do not need another chatbot that gives advice. They need an assistant that actually turns academic pressure into a plan. This is Luna Guardian.”

**0:15–0:50 — Lead with agent execution**

Use the microphone or paste: “I have a Java exam tomorrow, two assignments, and three hours available.”

“Luna understands the commitments, executes real tools, saves three tasks, and creates a deadline-prioritized study plan. These steps are not an animation: each tool name, argument set, result, and database change is recorded.”

Point to the priorities, schedule, upcoming deadlines, and activity timeline.

**0:50–1:20 — Prove persistence**

Refresh the page.

“The state survives refresh because tasks, plans, sessions, context, and progress are persisted in SQLite. The dashboard reads the saved state rather than reconstructing a conversation.”

Complete one task.

“Completing work updates the task and cancels its remaining planned sessions.”

**1:20–1:45 — Demonstrate adaptive replanning**

Choose “Missed” on a session and enter 120 remaining minutes.

“When a session is missed, Luna records that outcome, supersedes the old schedule, and builds a realistic replacement from the remaining work.”

**1:45–2:15 — Prove MCP interoperability**

Show the MCP client output.

“This is a real authenticated Streamable HTTP MCP server using the official Python SDK. The client negotiates protocol 2025-11-25, discovers all nine tools, and executes the same persistence operations used by the simulator.”

**2:15–2:40 — Voice, safety, and provider honesty**

“Browser speech provides microphone input, visible transcription, text fallback, and optional spoken replies. User data is isolated by bearer identity, input is validated, requests are rate-limited, and secrets stay in environment variables.”

If Bedrock is verified before recording: “The agent is powered by Amazon Bedrock through the Converse tool-use API.” Otherwise say: “Bedrock support is implemented but not claimed in this demo because credentials were unavailable for live verification.”

**2:40–2:55 — Close**

“Luna Guardian makes the next step visible, achievable, and adaptable—so students can spend less energy managing the plan and more energy doing the work.”
