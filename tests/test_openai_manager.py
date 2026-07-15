from types import SimpleNamespace

import pytest

import openai_manager as manager


class RecordingResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(output_text="Grounded answer")


def client_with_responses():
    responses = RecordingResponses()
    return SimpleNamespace(responses=responses), responses


def test_settings_require_key_and_vector_store():
    with pytest.raises(manager.ConfigurationError, match="API key"):
        manager.ConnectionSettings("", "vs_example").validated()
    with pytest.raises(manager.ConfigurationError, match="normally start"):
        manager.ConnectionSettings("unit-test-key", "wrong").validated()


def test_settings_are_trimmed():
    settings = manager.ConnectionSettings(
        "  unit-test-key  ", "  vs_example  ", "  pmpt_example  ", "  test-model  "
    ).validated()
    assert settings.api_key == "unit-test-key"  # pragma: allowlist secret
    assert settings.vector_store_id == "vs_example"
    assert settings.prompt_id == "pmpt_example"
    assert settings.model == "test-model"


def test_safe_error_redacts_supplied_and_openai_shaped_keys():
    secret = "unit-test-super-secret"  # pragma: allowlist secret
    openai_shaped = "sk-" + "abcdefghijklmnopqrstuvwxyz012345"
    message = manager.safe_error_message(RuntimeError(f"bad {secret} and {openai_shaped}"), secret)
    assert secret not in message
    assert openai_shaped not in message
    assert message.count("[redacted]") == 2


def test_ask_uses_prompt_id_and_does_not_store_response():
    client, responses = client_with_responses()
    result = manager.ask_store(
        client,
        "vs_example",
        "What is covered?",
        prompt_id="pmpt_example",
        max_results=4,
    )
    assert result.output_text == "Grounded answer"
    assert responses.kwargs["prompt"] == {"id": "pmpt_example"}
    assert responses.kwargs["store"] is False
    assert responses.kwargs["tools"][0]["vector_store_ids"] == ["vs_example"]
    assert "model" not in responses.kwargs
    assert "instructions" not in responses.kwargs


def test_ask_uses_code_managed_fallback_without_prompt_id():
    client, responses = client_with_responses()
    manager.ask_store(client, "vs_example", "Question", model="test-model")
    assert responses.kwargs["model"] == "test-model"
    assert responses.kwargs["instructions"] == manager.DEFAULT_INSTRUCTIONS
    assert "prompt" not in responses.kwargs


def test_validate_upload_rejects_empty_unsupported_and_oversized_files(monkeypatch):
    with pytest.raises(manager.ConfigurationError, match="empty"):
        manager.validate_upload("notes.md", b"")
    with pytest.raises(manager.ConfigurationError, match="Unsupported"):
        manager.validate_upload("payload.exe", b"content")
    monkeypatch.setattr(manager, "MAX_UPLOAD_BYTES", 3)
    with pytest.raises(manager.ConfigurationError, match="50 MB"):
        manager.validate_upload("notes.md", b"four")


def test_upload_cleans_up_source_file_if_attach_fails():
    deleted = []

    class Files:
        def create(self, **_kwargs):
            return SimpleNamespace(id="file_example")

        def delete(self, *, file_id):
            deleted.append(file_id)

    class StoreFiles:
        def create_and_poll(self, **_kwargs):
            raise RuntimeError("attach failed")

    client = SimpleNamespace(
        files=Files(),
        vector_stores=SimpleNamespace(files=StoreFiles()),
    )
    with pytest.raises(RuntimeError, match="attach failed"):
        manager.upload_file(client, "vs_example", "notes.md", b"content")
    assert deleted == ["file_example"]


def test_response_sources_are_unique_and_sorted():
    annotation_a = SimpleNamespace(filename="zeta.pdf")
    annotation_b = SimpleNamespace(filename="alpha.md")
    content = SimpleNamespace(text="Answer", annotations=[annotation_a, annotation_b, annotation_a])
    response = SimpleNamespace(output=[SimpleNamespace(content=[content])])
    assert manager.response_sources(response) == ["alpha.md", "zeta.pdf"]
