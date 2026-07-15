# Security policy

## Reporting

Please report suspected credential exposure or security issues privately to the repository owner. Do not include live API keys, document contents, or full OpenAI error payloads in a public issue.

## Supported configuration

- Prefer project-scoped OpenAI API keys with only the access required by this app.
- Enter credentials only in a local instance or a trusted HTTPS deployment you control.
- Credentials are accepted only through the session UI; server environment variables and Streamlit secrets are intentionally ignored.
- Never commit `.env`, `.streamlit/secrets.toml`, databases, logs, or exported Vector Store content.
- Rotate a key immediately if it may have been exposed, including in Git history.

## Deployment boundary

This repository does not contain user authentication, rate limiting, or multi-user secret storage. Do not attach an owner's API key to a public deployment. Anyone using the app should provide credentials for their own OpenAI project and must trust the server operator because form values are processed by the Streamlit server.

## Remote side effects

Uploads, Vector Store detach operations, and optional source-file deletion change resources in the connected OpenAI project. Review the selected Vector Store ID and file IDs before confirming a destructive operation.
