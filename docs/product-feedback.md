# Product feedback draft

Use this as a source for Devpost's required Product Feedback answer. Remove any integration that is not part of the final submitted build, replace the bracketed LLM row after live verification, and keep claims tied to observed behavior.

## Model Context Protocol Python SDK

- **Used for:** A self-hosted MCP server and authenticated Streamable HTTP client calls from the live agent, including tool discovery and execution.
- **Worked well:** FastMCP made typed tools concise; the official client made protocol negotiation and real call results observable; one domain layer could serve both MCP and REST consumers.
- **Needs work:** The session manager is one-shot within a process, the mounted path redirects to its trailing-slash form, and production reverse-proxy host allowlisting was not obvious from starter guidance.
- **Onboarding:** Quick for a local hello world, with extra investigation needed for repeatable tests and public deployment.
- **Build again:** Yes. The protocol boundary makes agent actions independently inspectable and portable.

## FastAPI and Pydantic

- **Used for:** The web application, authenticated REST API, validation models, health endpoint, and MCP mounting/lifecycle.
- **Worked well:** Typed request validation, dependency-based user isolation, and ASGI composition were productive and reliable.
- **Needs work:** Sync endpoint/thread-pool behavior and nested loopback MCP requests require careful deployment testing and documentation.
- **Onboarding:** Straightforward because both libraries have clear Python-first patterns.
- **Build again:** Yes, especially for a compact API-and-agent service.

## PostgreSQL and psycopg

- **Used for:** Durable tasks, plans, study sessions, student context, and the agent activity ledger.
- **Worked well:** Transactions and relational constraints made real persistence easy to verify independently of the UI.
- **Needs work:** A free hosted database has an expiration date and needs explicit lifecycle planning for a judging window.
- **Onboarding:** The adapter required more work than local SQLite but removed the need for a paid persistent disk.
- **Build again:** Yes for production or multi-instance deployment.

## Render

- **Used for:** Public Docker web-service hosting, environment-secret management, health checks, logs, and managed PostgreSQL.
- **Worked well:** Blueprint configuration, GitHub auto-deploys, managed database wiring, and public HTTPS produced a reproducible demo environment.
- **Needs work:** Persistent disks silently move the web service off the free plan; free services cold-start; the free PostgreSQL instance expires after 30 days.
- **Onboarding:** Smooth after the plan and DNS-rebinding issues were understood, but the pricing transition should be surfaced earlier.
- **Build again:** Yes for hackathon demos, with explicit cost and database-expiry checks.

## Web Speech API

- **Used for:** Progressive-enhancement microphone transcription and optional synthesized spoken replies in supported browsers.
- **Worked well:** It adds voice without blocking typed input or requiring a separate voice backend.
- **Needs work:** Browser support and microphone permission behavior vary, so it cannot be the only input path.
- **Onboarding:** Minimal code, but true device/browser testing is essential.
- **Build again:** Yes as an enhancement with a visible text fallback, not as a universal voice layer.

## Actual LLM provider

- **Used for:** [Replace after live verification: model name/API] interprets natural language and independently selects MCP tools.
- **Worked well:** [Record observed tool-selection quality, latency, and final-response quality.]
- **Needs work:** [Record any schema compatibility, quota, latency, or reliability issues.]
- **Onboarding:** [Record the real credential/model setup experience.]
- **Build again:** [Yes/No with evidence-based reason.]

## Amazon services and Alexa+

No Amazon-hosted API, SDK, gated Alexa+ tool, device invocation, or AWS service was verified in this build. The Alexa+ entry uses the official rules' self-hosted MCP server and web-based simulated-experience path. Amazon Bedrock support exists in code but is not a working-integration claim and does not establish AWS Builder eligibility.
