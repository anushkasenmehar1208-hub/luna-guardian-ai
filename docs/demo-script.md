# Luna Guardian demo script (under 3 minutes)

**0:00–0:15 — Open on the live dashboard**

“Students do not need another chatbot that gives advice. They need an assistant that actually turns academic pressure into a plan. This is Luna Guardian.”

**0:15–0:50 — Lead with agent execution**

Use the microphone or paste: “I have a Java exam tomorrow. Create a revision task and schedule two hours of study.”

“The language model interprets the request and selects `create_task` and `create_study_plan`. Those calls travel through Luna's authenticated MCP endpoint, persist the task and sessions, and return their real results. These steps are not an animation: each request ID, tool name, argument set, result, and database change is recorded.”

Point to the priorities, schedule, upcoming deadlines, and activity timeline.

**0:50–1:20 — Prove persistence**

Refresh the page.

“The state survives refresh because tasks, plans, sessions, context, and progress are persisted in PostgreSQL. The dashboard reads the saved state rather than reconstructing a conversation.”

Complete one task.

“Completing work updates the task and cancels its remaining planned sessions.”

**1:20–1:45 — Demonstrate adaptive replanning**

Choose “Missed” on a session and enter 120 remaining minutes.

“When a session is missed, Luna records that outcome, supersedes the old schedule, and builds a realistic replacement from the remaining work.”

**1:45–2:15 — Prove MCP interoperability**

Show the MCP client output.

“This is a real authenticated Streamable HTTP MCP server using the official Python SDK. The client negotiates protocol 2025-11-25, discovers all nine tools, and the live agent invokes those tools through this endpoint.”

**2:15–2:40 — Voice, safety, and provider honesty**

“Browser speech provides microphone input, visible transcription, text fallback, and optional spoken replies. User data is isolated by bearer identity, input is validated, requests are rate-limited, and secrets stay in environment variables.”

Name only the provider shown in the live status bar. Do not say that Luna is powered by Amazon Bedrock unless a credentialed live Bedrock run has been captured and verified. No official Alexa+ device or gated-tool integration is claimed; this is the self-hosted-MCP web simulation path described in the event FAQ.

**2:40–2:55 — Close**

“Luna Guardian makes the next step visible, achievable, and adaptable—so students can spend less energy managing the plan and more energy doing the work.”
