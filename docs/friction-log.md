# Development friction log

All entries below came from this build session on October 22, 2026.

## 1. Clean test collection failed

- **Attempted task:** Establish the starter's automated-test baseline.
- **Steps taken:** Created a clean virtual environment, installed `requirements.txt`, and ran `pytest -q` from the project root.
- **Expected result:** The two starter tests would collect and run.
- **Actual result:** Collection stopped with `ModuleNotFoundError: No module named 'app'`.
- **Severity:** High — no regression signal was available from the documented command.
- **Workaround:** Added project-level pytest import configuration and replaced the narrow tests with domain/API scenarios.
- **Suggested improvement:** Ship a `pyproject.toml` or installable package in starter repositories.

## 2. MCP manager cannot be restarted in one process

- **Attempted task:** Run several API tests, each with its own `TestClient` lifespan.
- **Steps taken:** Started and closed a new FastAPI test client in three tests.
- **Expected result:** Each isolated test client would restart the app and MCP lifespan.
- **Actual result:** The official SDK raised `StreamableHTTPSessionManager .run() can only be called once per instance` on the second startup.
- **Severity:** Medium — production startup is unaffected, but common test isolation fails.
- **Workaround:** Reused one module-scoped app client while retaining per-test database isolation.
- **Suggested improvement:** Document the one-shot lifecycle prominently or expose a supported test factory pattern.

## 3. Streamable HTTP mount redirects without trailing slash

- **Attempted task:** Connect the official MCP client to `/mcp`.
- **Steps taken:** Initialized the client and ran discovery/calls.
- **Expected result:** Direct MCP response at the documented mount path.
- **Actual result:** The server returned HTTP 307 to `/mcp/`, after which the client followed the redirect and succeeded.
- **Severity:** Low — current clients follow the redirect, but strict clients or signature schemes may not.
- **Workaround:** Document `/mcp/` as the canonical endpoint.
- **Suggested improvement:** Make mount-path slash behavior explicit in FastMCP examples.

## 4. AWS feasibility blocked by missing local access

- **Attempted task:** Determine whether Amazon Bedrock could be live-integrated.
- **Steps taken:** Checked for the AWS CLI, attempted an STS identity lookup, and checked only credential-related environment variable names.
- **Expected result:** A usable AWS identity or clear authorization failure.
- **Actual result:** The AWS CLI was not installed and no AWS/Bedrock credential variables were present.
- **Severity:** High for the AWS Builder mini-challenge; none for the provider-neutral application.
- **Workaround:** Implemented a configurable Bedrock provider without claiming it works, retained other provider paths, and documented the exact verification gap.
- **Suggested improvement:** Provide hackathon participants with a credential-readiness checklist and a minimal Bedrock access verification command.

## 5. GitHub-hosted CI blocked before execution

- **Attempted task:** Run the already passing test and lint commands on every push in GitHub Actions.
- **Steps taken:** Added a Python 3.12 workflow to both public repositories and pushed it to `main`.
- **Expected result:** GitHub would provision an `ubuntu-latest` runner and execute installation, lint, compilation, and tests.
- **Actual result:** The first job ended before any step ran with: “The job was not started because your account is locked due to a billing issue.”
- **Severity:** Medium — local verification is complete, but hosted CI cannot provide an independent green run.
- **Workaround:** Retained the workflow files and the successful local command evidence; did not retry an account-level failure.
- **Suggested improvement:** Resolve the GitHub billing lock, then rerun the existing workflows without code changes.
