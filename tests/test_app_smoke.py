import hashlib

from streamlit.testing.v1 import AppTest


def clean_app(monkeypatch):
    for name in ("OPENAI_API_KEY", "OPENAI_VECTOR_STORE_ID", "OPENAI_PROMPT_ID"):
        monkeypatch.delenv(name, raising=False)
    return AppTest.from_file("app.py", default_timeout=10).run()


def test_overview_renders_labeled_connection_form(monkeypatch):
    app = clean_app(monkeypatch)
    assert not app.exception
    assert any("app you do not control" in warning.value for warning in app.warning)
    assert [item.label for item in app.text_input] == [
        "OpenAI API key",
        "Vector Store ID",
        "Prompt ID (optional, legacy)",
        "Fallback model",
    ]
    assert [item.label for item in app.radio] == ["Navigation"]
    assert "Connect" in [item.label for item in app.button]


def test_empty_connection_submission_shows_inline_error(monkeypatch):
    app = clean_app(monkeypatch)
    next(button for button in app.button if button.label == "Connect").click().run()
    assert not app.exception
    assert any("API key" in error.value for error in app.error)


def test_connected_navigation_and_disabled_ask_state(monkeypatch):
    app = clean_app(monkeypatch)
    app.text_input[0].set_value("unit-test-key")
    app.text_input[1].set_value("vs_example")
    app.run()

    fingerprint = hashlib.sha256(b"unit-test-key|vs_example").hexdigest()
    app.session_state["store_summary"] = {
        "id": "vs_example",
        "name": "Test Store",
        "status": "completed",
        "total": 2,
        "completed": 2,
        "in_progress": 0,
        "failed": 0,
    }
    app.session_state["connection_fingerprint"] = fingerprint
    app.run()
    assert [(metric.label, metric.value) for metric in app.metric] == [
        ("Total files", "2"),
        ("Ready", "2"),
        ("Processing", "0"),
        ("Failed", "0"),
    ]

    app.radio[0].set_value("Ask").run()
    assert not app.exception
    assert [title.value for title in app.title] == ["Ask"]
    ask_button = next(button for button in app.button if button.label == "Ask with file search")
    assert ask_button.disabled is True
