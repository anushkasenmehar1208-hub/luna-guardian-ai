# Amazon Developer Hackathon submission audit

Audit date: October 22, 2026. Primary track: **Alexa+**, using the permitted self-hosted MCP server plus web-based simulated-experience path. This is not a claim of official Alexa+ device integration.

Official sources: [requirements and submission fields](https://amazonappdev2026.devpost.com/), [official rules](https://amazonappdev2026.devpost.com/rules), and [FAQ](https://amazonappdev2026.devpost.com/details/faqs).

## Eligibility and entry

| Requirement | Status | Evidence or action |
|---|---|---|
| Entrant is at least the age of majority where they reside | Entrant confirmation required | This is a personal/legal fact and cannot be inferred from the repository. |
| Entrant is not in an excluded jurisdiction or conflict category | Entrant confirmation required | Sri Lanka is not specifically named in the exclusions, but the entrant must confirm all eligibility and conflict conditions. |
| Devpost account and “Join Hackathon” registration | Not verified | Confirm in Devpost before submission. |
| Submit by Oct 23, 2026 at 12:00pm PDT | Pending | Do not wait for the judging period. |
| Team/organization has an authorized representative, if applicable | Entrant confirmation required | Mark not applicable for a solo entry. |
| No prohibited Sponsor/Administrator financial or preferential support | Entrant confirmation required | The entrant must attest to this. |

## Working project and track requirements

| Requirement | Status | Evidence or action |
|---|---|---|
| New project or significant update during the submission window | Pass for new-project path, subject to entrant attestation | Repository history dates the implementation to the event window; describe this as a new build. |
| Working Alexa+ track project | Pass, self-hosted MCP/web-simulation path | FastAPI web app and MCP server are implemented in runtime code. |
| MCP spec 2025-11-25 or later | Pass, live | Final-deploy logs recorded protocol negotiation at `2025-11-25`. |
| Streamable HTTP transport | Pass, live | Canonical endpoint is `/mcp/` over HTTPS; the exact live agent run produced successful MCP POSTs and two `CallToolRequest` records. |
| Track technology imported and actually called at runtime | Pass, live | The original exact workflow used `gemini-3.1-flash-lite` to select `create_task` and `create_study_plan`, preserving request `673663b9-1d2f-4ae5-9c14-97cedfae3e0d`. After moving to the current free-tier `gemini-3.5-flash-lite`, a fresh live request selected and executed `list_tasks` through MCP under request `6c455857-17da-4883-ba10-21bbe91c4c13`. |
| Functioning project shown on its intended platform | Pending video | Record the live web simulation and public MCP proof. No physical Alexa device is required by the FAQ. |
| Authorized third-party SDK/API/data use | Review required | Comply with the MCP SDK, LLM provider, Render, PostgreSQL, and browser API terms. |

## Repository and testing access

| Requirement | Status | Evidence or action |
|---|---|---|
| GitHub repository | Pass | `https://github.com/anushkasenmehar1208-hub/luna-guardian-ai` |
| All source, assets, setup, and run instructions included | Pass with final review | README, Dockerfile, requirements, Render Blueprint, app, dashboard, tests, and docs are present. |
| Public repository with detectable open-source license | Pass | Root `LICENSE` is MIT and GitHub displays “MIT license” in the About panel. |
| Project free and accessible to judges through the judging period | Blocked on private credential handoff | Keep Render running through Nov 20, 2026. Put the bearer token only in Devpost's private testing instructions; never commit it. The free PostgreSQL instance expires Nov 21, 2026, one day after judging ends. |
| English submission materials and code documentation | Pass | Current materials are in English. |

## Required submission content

| Requirement | Status | Evidence or action |
|---|---|---|
| Text description explaining features and functionality | Draft ready | `docs/devpost-story.md` |
| Demo video under 3 minutes | Blocker | Record a final live run; keep the finished video below 3:00. |
| Public YouTube or Vimeo URL | Blocker | Upload the English video publicly and paste the URL into Devpost. |
| Video shows the project functioning | Blocker until recorded | Use the exact Java request, refresh persistence proof, dashboard timeline, voice/text fallback, and MCP protocol/tool discovery. |
| No unlicensed trademarks, music, or footage | Pending video review | Use original screen capture and narration; omit music unless licensed. |
| Product feedback for every tool/API/SDK | Draft ready for final form | `docs/product-feedback.md` covers MCP Python SDK, FastAPI/Pydantic, PostgreSQL/psycopg, Render, Web Speech API, and the verified Gemini API/model. |
| Primary track identified | Ready | Alexa+ |
| Existing-project changes described, if applicable | Not applicable if submitted as new | If the entrant says it predates Aug 31, add a precise before/after explanation and show it in the video. |
| Optional feature requests | Optional | Add only if useful. |
| Optional friction log for up to 10% bonus | Ready | `docs/friction-log.md` contains the required task, steps, expected/actual, severity, workaround, and suggestion fields. |

## Mini challenges

| Mini challenge | Status | Evidence or action |
|---|---|---|
| AWS Builder | **Do not enter yet** | Bedrock code exists, but no credentialed AWS service call has been verified. This does not establish eligibility. |
| Open Source | Ready, subject to entrant selecting it | The separate public [Luna MCP Study Planner Toolkit](https://github.com/anushkasenmehar1208-hub/luna-mcp-study-planner-toolkit) has its own MIT license, reusable API, tests, and event-window commit history. Provide that URL, the [primary repo](https://github.com/anushkasenmehar1208-hub/luna-guardian-ai), GitHub username `anushkasenmehar1208-hub`, and what/how/why text. |

## Ownership and compliance attestations

The entrant must personally confirm originality, sole ownership or authorized team ownership, third-party-license compliance, privacy rights, absence of infringing materials, eligibility, and any team representative authority. Those facts cannot be proven by an automated code audit.

## Final no-submit checklist

1. In a supported browser with a real microphone, record one visible speech-to-transcript attempt; text fallback and spoken-reply controls are already verified.
2. Record and upload the sub-three-minute public English video.
3. Add the live bearer credential only to private Devpost testing instructions.
4. Include the verified additional open-source repository URL and required what/how/why explanation if entering that mini challenge.
5. Select Alexa+ and, if desired, Open Source; do not select AWS Builder without a real AWS integration.
6. Review entrant eligibility/ownership attestations and submit before the deadline. This repository audit does not submit anything.
