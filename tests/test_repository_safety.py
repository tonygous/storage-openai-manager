import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", ".pytest_cache", ".ruff_cache", "__pycache__", ".venv"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".pyc"}
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SENSITIVE_PATTERNS = {
    "GitHub token": re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    "GitHub fine-grained token": re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    "AWS access key": re.compile(r"AKIA[A-Z0-9]{16}"),
    "Google API key": re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "Private key": re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
FORBIDDEN_BUSINESS_TERMS = (
    "me" + "xem",
    "ib" + "kr",
    "interactive" + " brokers",
)


def project_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not any(part in IGNORED_PARTS for part in path.parts):
            yield path


def test_repository_has_no_runtime_data_artifacts():
    unsafe = [
        str(path.relative_to(ROOT))
        for path in project_files()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.startswith(".env")
    ]
    assert unsafe == []


def test_public_app_has_no_server_credential_fallbacks():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    forbidden = ("st.secrets", "os.getenv", "OPENAI_API_KEY", "OPENAI_VECTOR_STORE_ID")
    assert [value for value in forbidden if value in source] == []


def test_repository_has_no_openai_shaped_secret_values():
    matches = []
    for path in project_files():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SECRET_PATTERN.search(text):
            matches.append(str(path.relative_to(ROOT)))
    assert matches == []


def test_repository_has_no_other_common_secret_formats_or_email_addresses():
    matches = []
    for path in project_files():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(text):
                matches.append(f"{path.relative_to(ROOT)}: {label}")
        if EMAIL_PATTERN.search(text):
            matches.append(f"{path.relative_to(ROOT)}: email address")
    assert matches == []


def test_repository_has_no_source_business_content():
    matches = []
    for path in project_files():
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in FORBIDDEN_BUSINESS_TERMS:
            if term in text:
                matches.append(f"{path.relative_to(ROOT)}: {term}")
    assert matches == []
