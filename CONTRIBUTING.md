# Contributing

Thanks for considering a contribution.

## Before you start

- Use a GitHub issue for reproducible bugs or a focused feature proposal.
- Do not post API keys, document contents, full OpenAI error payloads, or other sensitive data.
- Report suspected security issues using the private process in [SECURITY.md](SECURITY.md).

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Checks

Run the same checks used by CI:

```powershell
python -m ruff check .
python -m pytest
```

## Pull requests

- Keep each pull request focused on one change.
- Explain the user-visible effect and any remote OpenAI resource operations.
- Add or update tests for behavior changes.
- Update the README when configuration or usage changes.
- Confirm that no credentials, customer data, private documents, databases, logs, or company-specific material are included.
