# Security policy

## Reporting

Please report suspected credential exposure or security issues privately to the repository owner. Do not include live API keys, document contents, or full OpenAI error payloads in a public issue.

## Supported configuration

- Prefer project-scoped OpenAI API keys with only the access required by this app.
- Keep secrets in the session UI, process environment, or private hosting secrets.
- Never commit `.env`, `.streamlit/secrets.toml`, databases, logs, or exported Vector Store content.
- Rotate a key immediately if it may have been exposed, including in Git history.

## Remote side effects

Uploads, Vector Store detach operations, and optional source-file deletion change resources in the connected OpenAI project. Review the selected Vector Store ID and file IDs before confirming a destructive operation.
