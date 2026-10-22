# Amazon developer product feedback

## Verified usage status

No Amazon developer API, SDK, or hosted service was successfully used in the current local build. The machine had no AWS CLI and exposed no AWS credential environment variables. Therefore this project does **not** currently claim AWS Builder eligibility or a verified Amazon Bedrock integration.

## Amazon Bedrock integration path

- **Intended use:** LLM reasoning and tool selection through the Bedrock Runtime Converse API.
- **Implemented:** A configurable `bedrock` provider maps Luna's nine tools to Bedrock tool specifications and executes returned tool-use blocks through the real persistence layer.
- **What worked locally:** Static implementation, import isolation, and the provider-independent tool dispatcher.
- **What could not be verified:** Authentication, model access, request/response compatibility in an AWS account, latency, quotas, IAM policy, and regional model availability.
- **Onboarding experience:** Blocked before AWS onboarding because no credentials or CLI were available on the development machine.
- **Would we use it again:** Yes, after a credentialed smoke test confirms the selected model and region. Until then, this is an implementation candidate, not evidence of working AWS usage.

## Alexa+ track positioning

Luna is an Alexa+-style web simulation backed by a real MCP server. No official Alexa+ account integration, device invocation, or Amazon certification was implemented or verified. The submission and demo should retain this wording.
