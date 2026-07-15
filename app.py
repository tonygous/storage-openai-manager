"""Streamlit interface for Storage OpenAI Manager."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from openai_manager import (
    DEFAULT_MODEL,
    ConnectionSettings,
    accepted_upload_types,
    ask_store,
    connect_to_store,
    create_client,
    detach_file,
    human_bytes,
    list_store_files,
    response_sources,
    response_text,
    safe_error_message,
    search_store,
    upload_file,
)

APP_NAME = "Storage OpenAI Manager"

st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --som-bg: #0f172a;
            --som-surface: #10192e;
            --som-surface-2: #162238;
            --som-border: rgba(255, 255, 255, 0.12);
            --som-text: #f8fafc;
            --som-muted: #b8c4d6;
            --som-accent: #10b981;
            --som-focus: #60a5fa;
            --som-danger: #f87171;
            --som-radius: 12px;
        }
        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
        .stApp { background: var(--som-bg); color: var(--som-text); }
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
        [data-testid="stSidebar"] { border-right: 1px solid var(--som-border); }
        [data-testid="stMetric"] {
            min-height: 108px;
            background: var(--som-surface);
            border: 1px solid var(--som-border);
            border-radius: var(--som-radius);
            padding: 1rem;
        }
        .som-hero {
            padding: 1.5rem 0 1rem;
            max-width: 760px;
        }
        .som-eyebrow {
            color: #6ee7b7;
            font-size: .78rem;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .som-hero h1 { font-size: clamp(2rem, 5vw, 3.35rem); line-height: 1.05; margin: .45rem 0 .9rem; }
        .som-hero p { color: var(--som-muted); font-size: 1.08rem; line-height: 1.65; max-width: 68ch; }
        .som-card {
            background: var(--som-surface);
            border: 1px solid var(--som-border);
            border-radius: var(--som-radius);
            padding: 1rem 1.1rem;
            margin: .75rem 0;
        }
        .som-card strong { color: #ffffff; }
        .som-muted { color: var(--som-muted); }
        .som-status {
            display: inline-flex;
            align-items: center;
            gap: .5rem;
            border: 1px solid var(--som-border);
            border-radius: 999px;
            padding: .38rem .7rem;
            font-size: .85rem;
            font-weight: 650;
        }
        .som-status::before { content: ""; width: .5rem; height: .5rem; border-radius: 50%; background: #94a3b8; }
        .som-status.connected::before { background: #34d399; box-shadow: 0 0 0 4px rgba(52,211,153,.12); }
        .som-status.connected { color: #a7f3d0; }
        .som-code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .86rem; }
        .stButton > button, .stDownloadButton > button { min-height: 44px; transition: border-color 180ms ease, background 180ms ease; }
        .stButton > button:focus-visible, input:focus-visible, textarea:focus-visible {
            outline: 3px solid var(--som-focus) !important;
            outline-offset: 2px;
        }
        [data-testid="stFileUploaderDropzone"] { min-height: 132px; border-color: var(--som-border); }
        [data-testid="stAlert"] { border-radius: var(--som-radius); }
        a { color: #7dd3fc; }
        @media (max-width: 640px) {
            .block-container { padding: 1rem .85rem 2rem; }
            .som-hero { padding-top: .5rem; }
            .som-card { padding: .85rem; }
            [data-testid="stMetric"] { min-height: 92px; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def current_settings() -> ConnectionSettings:
    return ConnectionSettings(
        api_key=st.session_state.get("api_key_input", "").strip(),
        vector_store_id=st.session_state.get("vector_store_input", "").strip(),
        prompt_id=st.session_state.get("prompt_id_input", "").strip() or None,
        model=st.session_state.get("model_input", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
    )


def settings_fingerprint(settings: ConnectionSettings) -> str:
    material = f"{settings.api_key}|{settings.vector_store_id}".encode()
    return hashlib.sha256(material).hexdigest()


def connected(settings: ConnectionSettings) -> bool:
    return bool(
        st.session_state.get("store_summary")
        and st.session_state.get("connection_fingerprint") == settings_fingerprint(settings)
    )


def disconnect() -> None:
    for key in (
        "api_key_input",
        "vector_store_input",
        "prompt_id_input",
        "store_summary",
        "connection_fingerprint",
        "file_rows",
        "search_results",
        "last_answer",
        "last_sources",
    ):
        st.session_state.pop(key, None)


def render_sidebar() -> tuple[str, ConnectionSettings, bool]:
    with st.sidebar:
        st.subheader(APP_NAME)
        st.caption("Connect to your existing OpenAI storage without saving credentials locally.")
        st.warning(
            "Only enter a key on a local or trusted HTTPS deployment. "
            "Never enter credentials into an app you do not control."
        )

        page = st.radio(
            "Navigation",
            ["Overview", "Files", "Search", "Ask"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown("#### Connection")
        st.text_input(
            "OpenAI API key",
            type="password",
            key="api_key_input",
            placeholder="Enter a project API key",
            help="Kept in this server-side Streamlit session and cleared with Clear session.",
        )
        st.text_input(
            "Vector Store ID",
            key="vector_store_input",
            placeholder="vs_...",
            help="Use the ID of an existing OpenAI Vector Store.",
        )
        st.text_input(
            "Prompt ID (optional, legacy)",
            key="prompt_id_input",
            placeholder="pmpt_...",
            help="If blank, the app uses its tested code-managed prompt and the model below.",
        )
        with st.expander("Advanced", expanded=False):
            st.text_input(
                "Fallback model",
                key="model_input",
                value=st.session_state.get("model_input", DEFAULT_MODEL),
                help="Used only when Prompt ID is blank.",
            )

        settings = current_settings()
        is_connected = connected(settings)
        status_class = "connected" if is_connected else ""
        status_label = "Connected" if is_connected else "Not connected"
        st.markdown(
            f'<span class="som-status {status_class}">{status_label}</span>',
            unsafe_allow_html=True,
        )

        if st.button("Connect", type="primary", use_container_width=True):
            try:
                valid = settings.validated()
                with st.spinner("Checking the Vector Store connection..."):
                    summary = connect_to_store(create_client(valid.api_key), valid.vector_store_id)
                st.session_state["store_summary"] = summary
                st.session_state["connection_fingerprint"] = settings_fingerprint(valid)
                st.session_state.pop("file_rows", None)
                st.success(f"Connected to {summary['name']}.")
                st.rerun()
            except Exception as exc:
                st.error(safe_error_message(exc, settings.api_key))

        st.button("Clear session", use_container_width=True, on_click=disconnect)
        st.caption("Nothing in this form is written to a project file or database.")
    return page, settings, connected(settings)


def require_connection(
    settings: ConnectionSettings, is_connected: bool
) -> tuple[Any, ConnectionSettings] | None:
    if not is_connected:
        st.info("Enter your API key and Vector Store ID in the sidebar, then select Connect.")
        return None
    try:
        valid = settings.validated()
        return create_client(valid.api_key), valid
    except Exception as exc:
        st.error(safe_error_message(exc, settings.api_key))
        return None


def page_overview(settings: ConnectionSettings, is_connected: bool) -> None:
    st.markdown(
        """
        <section class="som-hero">
          <div class="som-eyebrow">Stateless OpenAI storage utility</div>
          <h1>Manage one Vector Store without shipping its data.</h1>
          <p>Connect at runtime, inspect and upload files, test retrieval, and ask grounded questions. Credentials and content are never bundled with this project.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if not is_connected:
        st.info(
            "Start in the sidebar: add an API key and an existing Vector Store ID, then connect."
        )
        cols = st.columns(3)
        items = [
            ("1. Connect", "Use session-only credentials."),
            ("2. Inspect", "Review remote file status before changing anything."),
            ("3. Test", "Search first, then ask a grounded question."),
        ]
        for column, (title, body) in zip(cols, items, strict=True):
            with column:
                st.markdown(
                    f'<div class="som-card"><strong>{title}</strong><br><span class="som-muted">{body}</span></div>',
                    unsafe_allow_html=True,
                )
        return

    summary = st.session_state["store_summary"]
    st.success(f"Connected to {summary['name']}")
    cols = st.columns(4)
    for column, (label, value) in zip(
        cols,
        [
            ("Total files", summary.get("total", 0)),
            ("Ready", summary.get("completed", 0)),
            ("Processing", summary.get("in_progress", 0)),
            ("Failed", summary.get("failed", 0)),
        ],
        strict=True,
    ):
        column.metric(label, value)
    st.markdown(
        f'<div class="som-card"><strong>Vector Store</strong><br><span class="som-code">{summary["id"]}</span><br><span class="som-muted">Status: {summary["status"]}</span></div>',
        unsafe_allow_html=True,
    )
    if settings.prompt_id:
        st.warning(
            "This session will use a reusable Prompt ID. OpenAI is deprecating reusable prompt objects; "
            "the app also supports a code-managed fallback when this field is blank."
        )
    else:
        st.caption(f"Ask mode uses the code-managed grounding prompt with `{settings.model}`.")


def refresh_files(client: Any, settings: ConnectionSettings) -> list[dict[str, Any]]:
    with st.spinner("Reading Vector Store files…"):
        rows = list_store_files(client, settings.vector_store_id)
    st.session_state["file_rows"] = rows
    return rows


def page_files(settings: ConnectionSettings, is_connected: bool) -> None:
    st.title("Files")
    st.caption("Upload directly to the connected Vector Store or remove selected remote records.")
    connection = require_connection(settings, is_connected)
    if not connection:
        return
    client, valid = connection

    st.subheader("Upload")
    uploaded = st.file_uploader(
        "Choose files",
        type=accepted_upload_types(),
        accept_multiple_files=True,
        help="Files are sent to OpenAI only after you select Upload. This app does not save a local copy.",
    )
    upload_disabled = not uploaded
    if st.button("Upload to Vector Store", type="primary", disabled=upload_disabled):
        successes: list[str] = []
        failures: list[str] = []
        progress = st.progress(0, text="Preparing upload…")
        for index, item in enumerate(uploaded or [], start=1):
            try:
                result = upload_file(client, valid.vector_store_id, item.name, item.getvalue())
                successes.append(f"{result['filename']} ({result['status']})")
            except Exception as exc:
                failures.append(f"{item.name}: {safe_error_message(exc, valid.api_key)}")
            progress.progress(index / len(uploaded), text=f"Processed {index} of {len(uploaded)}")
        progress.empty()
        if successes:
            st.success("Uploaded: " + ", ".join(successes))
            st.session_state.pop("file_rows", None)
        if failures:
            st.error("Some uploads failed:\n\n" + "\n\n".join(failures))

    st.divider()
    col_title, col_action = st.columns([3, 1])
    col_title.subheader("Remote files")
    refresh_requested = col_action.button("Refresh", use_container_width=True)
    try:
        rows = st.session_state.get("file_rows")
        if rows is None or refresh_requested:
            rows = refresh_files(client, valid)
    except Exception as exc:
        st.error(safe_error_message(exc, valid.api_key))
        return

    if not rows:
        st.info("This Vector Store has no files yet. Upload a supported document above.")
        return

    display_rows = [
        {
            "filename": row["filename"],
            "status": row["status"],
            "size": human_bytes(row["size_bytes"]),
            "file_id": row["file_id"],
        }
        for row in rows
    ]
    st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)

    with st.expander("Remove files", expanded=False):
        st.warning(
            "Removing a record changes the live Vector Store. This cannot be undone in this app."
        )
        labels = {f"{row['filename']} — {row['file_id']}": row["file_id"] for row in rows}
        selected = st.multiselect("Files to remove", list(labels))
        delete_source = st.checkbox(
            "Also delete each underlying OpenAI File object",
            help="Leave this off to detach only from this Vector Store.",
        )
        confirmation = st.text_input("Type DELETE to confirm", key="delete_confirmation")
        can_delete = bool(selected) and confirmation == "DELETE"
        if st.button("Remove selected files", disabled=not can_delete):
            removed: list[str] = []
            failed: list[str] = []
            for label in selected:
                try:
                    detach_file(
                        client,
                        valid.vector_store_id,
                        labels[label],
                        delete_source_file=delete_source,
                    )
                    removed.append(label)
                except Exception as exc:
                    failed.append(f"{label}: {safe_error_message(exc, valid.api_key)}")
            if removed:
                st.success(f"Removed {len(removed)} file(s).")
                st.session_state.pop("file_rows", None)
            if failed:
                st.error("\n\n".join(failed))


def page_search(settings: ConnectionSettings, is_connected: bool) -> None:
    st.title("Search")
    st.caption("Test raw semantic and keyword retrieval before asking the model for an answer.")
    connection = require_connection(settings, is_connected)
    if not connection:
        return
    client, valid = connection

    query = st.text_input("Search query", placeholder="What does the knowledge base say about…?")
    max_results = st.slider("Maximum results", 1, 20, 5, key="search_max")
    if st.button("Search Vector Store", type="primary", disabled=not query.strip()):
        try:
            with st.spinner("Searching the Vector Store…"):
                st.session_state["search_results"] = search_store(
                    client,
                    valid.vector_store_id,
                    query,
                    max_results=max_results,
                )
        except Exception as exc:
            st.error(safe_error_message(exc, valid.api_key))

    results = st.session_state.get("search_results")
    if results is None:
        st.info("Run a search to verify that the expected source documents are retrievable.")
        return
    if not results:
        st.warning(
            "No matching passages were returned. Try broader wording or verify the file status."
        )
        return
    st.success(f"Found {len(results)} result(s).")
    for index, row in enumerate(results, start=1):
        score = row.get("score")
        score_label = f"{float(score):.3f}" if score is not None else "—"
        with st.expander(f"{index}. {row['filename']} · score {score_label}", expanded=index == 1):
            st.caption(row.get("file_id") or "No file ID returned")
            st.write(row.get("snippet") or "No passage text returned.")


def page_ask(settings: ConnectionSettings, is_connected: bool) -> None:
    st.title("Ask")
    st.caption(
        "Generate a grounded answer with Responses API file search. Responses are not stored by this app."
    )
    connection = require_connection(settings, is_connected)
    if not connection:
        return
    client, valid = connection

    if valid.prompt_id:
        st.info(
            "Using the Prompt ID entered in the sidebar. Clear it to use the code-managed fallback prompt."
        )
        st.warning(
            "Reusable prompt objects are deprecated by OpenAI and scheduled to shut down on November 30, 2026."
        )
    else:
        st.info(f"Using the code-managed grounding prompt with `{valid.model}`.")

    question = st.text_area(
        "Question",
        placeholder="Ask a question that should be answered from the connected files.",
        height=130,
    )
    max_results = st.slider("File-search results", 1, 20, 8, key="ask_max")
    if st.button("Ask with file search", type="primary", disabled=not question.strip()):
        try:
            with st.spinner("Searching sources and generating an answer…"):
                response = ask_store(
                    client,
                    valid.vector_store_id,
                    question,
                    prompt_id=valid.prompt_id,
                    model=valid.model,
                    max_results=max_results,
                )
            st.session_state["last_answer"] = response_text(response)
            st.session_state["last_sources"] = response_sources(response)
            st.session_state["last_answer_time"] = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        except Exception as exc:
            st.error(safe_error_message(exc, valid.api_key))

    answer = st.session_state.get("last_answer")
    if answer is not None:
        st.subheader("Answer")
        st.write(answer or "The API returned no text.")
        sources = st.session_state.get("last_sources") or []
        st.subheader("Sources")
        if sources:
            for source in sources:
                st.markdown(f"- `{source}`")
        else:
            st.caption("No source filenames were returned in response annotations.")
        st.caption(
            f"Generated {st.session_state.get('last_answer_time', '')}. Cleared when you clear this session."
        )


def main() -> None:
    inject_styles()
    page, settings, is_connected = render_sidebar()
    pages = {
        "Overview": page_overview,
        "Files": page_files,
        "Search": page_search,
        "Ask": page_ask,
    }
    pages[page](settings, is_connected)


if __name__ == "__main__":
    main()
