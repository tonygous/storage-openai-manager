# Storage OpenAI Manager

A clean, stateless Streamlit interface for connecting to an existing OpenAI Vector Store. It lets you inspect files, upload supported documents, test retrieval, and ask grounded questions through the Responses API.


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

The safest setup is to clone the project and run it locally. Only enter an API key into a local app or a trusted HTTPS deployment that you control. A third-party Streamlit deployment can receive values submitted through its form, even though this repository does not save them.

This app intentionally ignores server environment variables and Streamlit secrets for OpenAI credentials. That prevents visitors to a public deployment from silently using the deployment owner's key. Every user must enter credentials for their own OpenAI project in the current session.

The app does not include user authentication, rate limiting, or a credential vault, so it is not a turnkey public multi-user service. Add those controls before offering it as a hosted service to other people.

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

## Prompt ID compatibility

If a Prompt ID is supplied, the app sends it through the Responses API `prompt` parameter and adds the connected Vector Store as a `file_search` tool. If the field is blank, the app uses `gpt-5.6-luna` by default and a small, tested prompt in `openai_manager.py`. The model remains editable in the sidebar's Advanced section.

OpenAI now recommends code-managed prompts for new text-generation work. Reusable prompt-object creation was de-emphasized on June 3, 2026, and the `v1/prompts` endpoint is scheduled to shut down on November 30, 2026. The optional Prompt ID path remains here for existing integrations, while the fallback keeps the project migration-ready. See the official [text generation guidance](https://developers.openai.com/api/docs/guides/text#version-prompts-in-code) and [file search guide](https://developers.openai.com/api/docs/guides/tools-file-search).

## Run checks

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest
python -m bandit -q -r app.py openai_manager.py
python -m pip_audit -r requirements.txt -r requirements-dev.txt
```

The repository-safety tests fail if source-business content, an email address, any `.env` file, database, log, bytecode file, private key, or common API-token format is added to the project. CI also runs a high-entropy secret scan.

The included GitHub Actions workflow runs linting, tests, static security analysis, dependency auditing, and secret scanning on Python 3.10 and 3.12 for every push and pull request.

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
- **Vector Store not found:** verify the `vs_...` ID and project access.
- **Upload stays in progress:** refresh the Files page after OpenAI finishes processing.
- **Search returns nothing:** verify file status, then try broader wording.
- **Prompt request fails:** clear the Prompt ID and test the code-managed fallback. Existing saved prompts may also require variables that this generic manager does not know about.
- **No citations:** test Search directly; the model can only cite files returned by retrieval.

## Cost and data notice

OpenAI API usage, Vector Store storage, file search, and model generation may incur charges. Documents, questions, and generated answers are sent to OpenAI under the policies and retention settings of your OpenAI project. The local app does not add its own analytics or persistence.

## Support

If this project helps you, you can support continued maintenance through [Ko-fi](https://ko-fi.com/antongoren).

Crypto donations:

- **Ethereum (ETH):** `0x47388f869b6B34fa2CD0c6Bb7C2787B86407CcfF`
- **TRON:** `TF5NUf9eb7BPJ8HjCbSNFNaarHrtRTdbiA`
- **Solana:** `HWVY559mMwqhiumTmZpjDick6XaMjehQE7W4v7ec5Kvg`

Only send assets on the stated network. Cryptocurrency transfers are irreversible. Donations support documentation, testing, maintenance, and future releases; they do not purchase services or guarantee support.

## License

MIT. See [LICENSE](LICENSE).
