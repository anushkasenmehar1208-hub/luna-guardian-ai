# Security

## Deployment checklist

- Set `LUNA_ENV=production`; startup then requires explicit token configuration.
- Generate opaque, high-entropy bearer tokens and store `LUNA_AUTH_TOKENS` only in the host's secret manager.
- Never commit LLM or AWS credentials. Prefer workload roles for Bedrock.
- Serve only over HTTPS and rotate any token exposed in a recording or screenshot.
- Back up the persistent database and restrict file access to the service account.
- Use a managed identity service before supporting untrusted public sign-ups. The current token map is suitable for a controlled hackathon demo, not a general consumer launch.

Report suspected vulnerabilities privately to the repository owner. Do not include credentials or personal student data in a public issue.
