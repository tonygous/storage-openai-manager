"""OpenAI API operations for the stateless Storage OpenAI Manager."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_INSTRUCTIONS = (
    "Answer using the connected knowledge base. Cite the source filenames when "
    "possible. If the answer is not supported by the knowledge base, say so clearly."
)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
SUPPORTED_EXTENSIONS = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".doc",
    ".docx",
    ".go",
    ".html",
    ".java",
    ".js",
    ".json",
    ".md",
    ".pdf",
    ".php",
    ".pptx",
    ".py",
    ".rb",
    ".sh",
    ".tex",
    ".ts",
    ".txt",
}


class ConfigurationError(ValueError):
    """Raised when connection settings are incomplete or malformed."""


@dataclass(frozen=True)
class ConnectionSettings:
    api_key: str
    vector_store_id: str
    prompt_id: str | None = None
    model: str = DEFAULT_MODEL

    def validated(self) -> ConnectionSettings:
        api_key = self.api_key.strip()
        vector_store_id = self.vector_store_id.strip()
        prompt_id = (self.prompt_id or "").strip() or None
        model = self.model.strip() or DEFAULT_MODEL

        if not api_key:
            raise ConfigurationError("Enter an OpenAI API key.")
        if not vector_store_id:
            raise ConfigurationError("Enter an OpenAI Vector Store ID.")
        if not vector_store_id.startswith("vs_"):
            raise ConfigurationError("Vector Store IDs normally start with 'vs_'.")

        return ConnectionSettings(
            api_key=api_key,
            vector_store_id=vector_store_id,
            prompt_id=prompt_id,
            model=model,
        )


def create_client(api_key: str) -> OpenAI:
    if not api_key.strip():
        raise ConfigurationError("Enter an OpenAI API key.")
    return OpenAI(api_key=api_key.strip(), timeout=60.0, max_retries=2)


def safe_error_message(exc: Exception, api_key: str = "") -> str:
    """Return an actionable error without ever echoing a supplied API key."""
    message = " ".join(str(exc).split()) or exc.__class__.__name__
    if api_key:
        message = message.replace(api_key, "[redacted]")
    message = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[redacted]", message)
    return message[:900]


def connect_to_store(client: OpenAI, vector_store_id: str) -> dict[str, Any]:
    store = client.vector_stores.retrieve(vector_store_id=vector_store_id)
    counts = getattr(store, "file_counts", None)
    return {
        "id": str(getattr(store, "id", vector_store_id)),
        "name": getattr(store, "name", None) or "Unnamed vector store",
        "status": getattr(store, "status", None) or "unknown",
        "created_at": getattr(store, "created_at", None),
        "completed": getattr(counts, "completed", 0) if counts else 0,
        "in_progress": getattr(counts, "in_progress", 0) if counts else 0,
        "failed": getattr(counts, "failed", 0) if counts else 0,
        "cancelled": getattr(counts, "cancelled", 0) if counts else 0,
        "total": getattr(counts, "total", 0) if counts else 0,
    }


def _page_items(page: Any) -> list[Any]:
    auto_paging = getattr(page, "auto_paging_iter", None)
    if callable(auto_paging):
        return list(auto_paging())
    return list(getattr(page, "data", page) or [])


def list_store_files(client: OpenAI, vector_store_id: str) -> list[dict[str, Any]]:
    page = client.vector_stores.files.list(
        vector_store_id=vector_store_id,
        limit=100,
        order="desc",
    )
    rows: list[dict[str, Any]] = []
    for record in _page_items(page):
        file_id = str(getattr(record, "id", ""))
        filename = "Unavailable file"
        size_bytes = None
        purpose = None
        try:
            file_info = client.files.retrieve(file_id=file_id)
            filename = getattr(file_info, "filename", None) or filename
            size_bytes = getattr(file_info, "bytes", None)
            purpose = getattr(file_info, "purpose", None)
        except Exception:  # The vector-store record can outlive its file object.
            filename = "File object unavailable"
            purpose = "unavailable"
        rows.append(
            {
                "file_id": file_id,
                "filename": filename,
                "status": getattr(record, "status", None) or "unknown",
                "size_bytes": size_bytes,
                "purpose": purpose,
                "created_at": getattr(record, "created_at", None),
                "last_error": str(getattr(record, "last_error", None) or ""),
            }
        )
    return rows


def validate_upload(filename: str, content: bytes) -> str:
    safe_name = Path(filename).name.strip()
    if not safe_name:
        raise ConfigurationError("The uploaded file needs a filename.")
    if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ConfigurationError(f"Unsupported file type. Allowed types: {allowed}")
    if not content:
        raise ConfigurationError(f"'{safe_name}' is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ConfigurationError("Files must be 50 MB or smaller in this app.")
    return safe_name


def upload_file(
    client: OpenAI,
    vector_store_id: str,
    filename: str,
    content: bytes,
) -> dict[str, Any]:
    safe_name = validate_upload(filename, content)
    openai_file = client.files.create(
        file=(safe_name, content),
        purpose="assistants",
    )
    try:
        record = client.vector_stores.files.create_and_poll(
            vector_store_id=vector_store_id,
            file_id=openai_file.id,
        )
    except Exception:
        with suppress(Exception):
            client.files.delete(file_id=openai_file.id)
        raise
    return {
        "file_id": str(openai_file.id),
        "filename": safe_name,
        "status": getattr(record, "status", None) or "unknown",
    }


def detach_file(
    client: OpenAI,
    vector_store_id: str,
    file_id: str,
    *,
    delete_source_file: bool = False,
) -> dict[str, bool]:
    detached = client.vector_stores.files.delete(
        vector_store_id=vector_store_id,
        file_id=file_id,
    )
    source_deleted = False
    if delete_source_file:
        result = client.files.delete(file_id=file_id)
        source_deleted = bool(getattr(result, "deleted", False))
    return {
        "detached": bool(getattr(detached, "deleted", False)),
        "source_deleted": source_deleted,
    }


def search_store(
    client: OpenAI,
    vector_store_id: str,
    query: str,
    *,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    clean_query = query.strip()
    if not clean_query:
        raise ConfigurationError("Enter a search query.")
    result = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query=clean_query,
        max_num_results=max_results,
        rewrite_query=True,
    )
    rows: list[dict[str, Any]] = []
    for item in list(getattr(result, "data", []) or []):
        parts = getattr(item, "content", None) or []
        snippet = "\n\n".join(
            str(getattr(part, "text", None) or "").strip()
            for part in parts
            if getattr(part, "text", None)
        )
        rows.append(
            {
                "score": getattr(item, "score", None),
                "file_id": getattr(item, "file_id", None),
                "filename": getattr(item, "filename", None)
                or getattr(item, "file_name", None)
                or "Unknown file",
                "snippet": snippet,
            }
        )
    return rows


def ask_store(
    client: OpenAI,
    vector_store_id: str,
    question: str,
    *,
    prompt_id: str | None = None,
    model: str = DEFAULT_MODEL,
    max_results: int = 8,
) -> Any:
    clean_question = question.strip()
    if not clean_question:
        raise ConfigurationError("Enter a question.")
    request: dict[str, Any] = {
        "input": clean_question,
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": max_results,
            }
        ],
        "include": ["file_search_call.results"],
        "store": False,
    }
    if prompt_id and prompt_id.strip():
        request["prompt"] = {"id": prompt_id.strip()}
    else:
        request["model"] = model.strip() or DEFAULT_MODEL
        request["instructions"] = DEFAULT_INSTRUCTIONS
    return client.responses.create(**request)


def response_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if direct:
        return str(direct).strip()
    chunks: list[str] = []
    for output in getattr(response, "output", []) or []:
        for content in getattr(output, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    return "\n\n".join(chunks).strip()


def response_sources(response: Any) -> list[str]:
    sources: set[str] = set()
    for output in getattr(response, "output", []) or []:
        for content in getattr(output, "content", []) or []:
            for annotation in getattr(content, "annotations", []) or []:
                filename = getattr(annotation, "filename", None)
                if filename:
                    sources.add(str(filename))
        for result in getattr(output, "results", []) or []:
            filename = getattr(result, "filename", None)
            if filename:
                sources.add(str(filename))
    return sorted(sources)


def human_bytes(value: int | None) -> str:
    if value is None:
        return "—"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def accepted_upload_types() -> list[str]:
    return sorted(extension.removeprefix(".") for extension in SUPPORTED_EXTENSIONS)
