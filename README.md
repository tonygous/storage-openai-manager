# Storage OpenAI Manager

A clean, stateless Streamlit interface for connecting to an existing OpenAI Vector Store. It lets you inspect files, upload supported documents, test retrieval, and ask grounded questions through the Responses API.

No API key, Vector Store ID, Prompt ID, knowledge-base content, database, log, or response history is included in this repository.

## What it does

- Connects to one existing OpenAI Vector Store at runtime.
- Keeps UI-entered credentials in the current Streamlit session only.
- Lists remote files and their processing status.
- Uploads browser-selected files directly to OpenAI without saving local copies.
- Searches the Vector Store before model generation, which makes retrieval easier to test.
- Uses Responses API `file_search` for grounded answers and requests `store=False`.
- Supports an optional reusable Prompt ID and a code-managed fallback prompt.
- Requires an explicit `DELETE` confirmation before remote removal.
- Includes automated logic, safety, and secret-scanning tests.

## Security model

This project is stateless by design:

- The app does not write credentials to `.env`, Streamlit secrets, logs, or a database.
- The API key input is a password field and is redacted from displayed errors.
- `Clear session` removes connection values and generated output from Streamlit session state.
- Uploaded documents and file operations affect the OpenAI project associated with your API key.
- Removing a Vector Store record is a live remote action. Deleting the underlying File object is a separate opt-in.

Environment variables and Streamlit secrets are supported for private deployments. Never commit `.env` or `.streamlit/secrets.toml`; both are ignored by Git.

## Requirements

- Python 3.10 or newer
- An OpenAI API key with access to the target project
- An existing OpenAI Vector Store ID, normally beginning with `vs_`
- Optional: a reusable Prompt ID, normally beginning with `pmpt_`

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit. In the sidebar:

1. Enter your OpenAI API key.
2. Enter an existing Vector Store ID.
3. Optionally enter a Prompt ID.
4. Select **Connect**.

The fastest verification path is **Search** first, then **Ask**.

## Optional server configuration

Copy `.env.example` only for your own local setup and load those values in your shell or hosting service. The app checks these names:

```text
OPENAI_API_KEY
OPENAI_VECTOR_STORE_ID
OPENAI_PROMPT_ID
```

For Streamlit Community Cloud, add the same names in the app's private Secrets settings. Do not add a real `secrets.toml` to Git.

## Prompt ID compatibility

If a Prompt ID is supplied, the app sends it through the Responses API `prompt` parameter and adds the connected Vector Store as a `file_search` tool. If the field is blank, the app uses `gpt-5.6-luna` by default and a small, tested prompt in `openai_manager.py`. The model remains editable in the sidebar's Advanced section.

OpenAI now recommends code-managed prompts for new text-generation work. Reusable prompt-object creation was de-emphasized on June 3, 2026, and the `v1/prompts` endpoint is scheduled to shut down on November 30, 2026. The optional Prompt ID path remains here for existing integrations, while the fallback keeps the project migration-ready. See the official [text generation guidance](https://developers.openai.com/api/docs/guides/text#version-prompts-in-code) and [file search guide](https://developers.openai.com/api/docs/guides/tools-file-search).

## Run checks

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
```

The repository-safety tests fail if source-business content, an email address, `.env`, database, log, bytecode file, private key, or common API-token format is added to the project.

The included GitHub Actions workflow runs the same lint and test suite on Python 3.10 and 3.12 for every push and pull request.

## Contributing

Bug reports and focused pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and [SECURITY.md](SECURITY.md) for private security reporting guidance.

## Project layout

```text
app.py                  Streamlit UI and session-only configuration
openai_manager.py       Testable OpenAI API operations
tests/                  Logic and repository-safety tests
.streamlit/config.toml  Accessible dark theme and upload limit
design-system/          UI decisions generated for this project
```

## Troubleshooting

- **Authentication error:** confirm that the key belongs to the same OpenAI project as the Vector Store.
- **Vector Store not found:** verify the `vs_…` ID and project access.
- **Upload stays in progress:** refresh the Files page after OpenAI finishes processing.
- **Search returns nothing:** verify file status, then try broader wording.
- **Prompt request fails:** clear the Prompt ID and test the code-managed fallback. Existing saved prompts may also require variables that this generic manager does not know about.
- **No citations:** test Search directly; the model can only cite files returned by retrieval.

## Cost and data notice

OpenAI API usage, Vector Store storage, file search, and model generation may incur charges. Documents, questions, and generated answers are sent to OpenAI under the policies and retention settings of your OpenAI project. The local app does not add its own analytics or persistence.

## License

MIT. See [LICENSE](LICENSE).
