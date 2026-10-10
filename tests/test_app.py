"""Deterministic contract tests: no credentials, provider calls or telemetry."""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ["DD_LLMOBS_ENABLED"] = "0"
os.environ["DD_TRACE_ENABLED"] = "0"
os.environ["DD_INSTRUMENTATION_TELEMETRY_ENABLED"] = "0"

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app import MAX_NOTES_LENGTH, app, get_client


def completion(content, finish_reason="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )


@pytest.fixture
def api():
    provider = MagicMock()
    app.dependency_overrides[get_client] = lambda: provider
    with TestClient(app) as client:
        yield client, provider.chat.completions.create
    app.dependency_overrides.clear()


def test_health_without_credentials(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/docs").status_code == 200
        assert client.post("/summarize", json={"text": "Notes"}).status_code == 503


@pytest.mark.parametrize("endpoint", ["summarize", "flashcards", "quiz"])
@pytest.mark.parametrize(
    "body", [{}, {"text": ""}, {"text": "  \n "}, {"text": 7}, {"text": "x" * (MAX_NOTES_LENGTH + 1)}]
)
def test_invalid_input_never_calls_provider(api, endpoint, body):
    client, create = api
    assert client.post(f"/{endpoint}", json=body).status_code == 422
    create.assert_not_called()


def test_summary(api, monkeypatch):
    client, create = api
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    create.return_value = completion("A short summary.")
    response = client.post("/summarize", json={"text": "Study notes"})
    assert response.json() == {"summary": "A short summary."}
    assert create.call_args.kwargs["model"] == "test-model"


def test_flashcards_parsed(api):
    client, create = api
    cards = {"flashcards": [{"question": f"Q{i}?", "answer": "Answer"} for i in range(5)]}
    create.return_value = completion(json.dumps(cards))
    response = client.post("/flashcards", json={"text": "Study notes"})
    assert response.status_code == 200
    assert response.json() == cards


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        "```json\n{}\n```",
        "{}",
        json.dumps({"flashcards": [{"question": "Q?", "answer": " "}] * 5}),
        json.dumps({"flashcards": [{"question": "Q?", "answer": "A"}] * 4}),
        json.dumps({"flashcards": [{"question": "Q?"}] * 5}),
    ],
)
def test_bad_flashcards_are_application_errors(api, output):
    client, create = api
    create.return_value = completion(output)
    response = client.post("/flashcards", json={"text": "Notes"})
    assert response.status_code == 502
    assert response.json() == {"detail": "The model returned invalid Flashcards JSON."}


@pytest.mark.parametrize("verdict", ["supported", "unsupported", "uncertain"])
def test_quiz_checks_the_generated_answer_against_notes(api, verdict):
    client, create = api
    create.side_effect = [
        completion('{"question":"What is ATP?","answer":"An energy carrier."}'),
        completion(json.dumps({"verdict": verdict, "explanation": "Compared with source."})),
    ]
    response = client.post("/quiz", json={"text": "ATP carries energy in cells."})
    assert response.status_code == 200
    assert response.json()["self_check"]["verdict"] == verdict
    assert create.call_count == 2
    check_input = create.call_args.kwargs["messages"][1]["content"]
    assert "ATP carries energy in cells." in check_input
    assert "An energy carrier." in check_input


def test_invalid_quiz_draft_does_not_trigger_second_call(api):
    client, create = api
    create.return_value = completion("not JSON")
    assert client.post("/quiz", json={"text": "Notes"}).status_code == 502
    assert create.call_count == 1


def test_invalid_quiz_verdict(api):
    client, create = api
    create.side_effect = [
        completion('{"question":"Q?","answer":"A"}'),
        completion('{"verdict":"certainly","explanation":"Trust me"}'),
    ]
    assert client.post("/quiz", json={"text": "Notes"}).status_code == 502


@pytest.mark.parametrize(
    "content,reason", [(None, "stop"), (" ", "stop"), ("truncated", "length"), (None, "content_filter")]
)
def test_incomplete_outputs(api, content, reason):
    client, create = api
    create.return_value = completion(content, reason)
    assert client.post("/summarize", json={"text": "Notes"}).status_code == 502


@pytest.mark.parametrize("kind,status", [("timeout", 504), ("rate", 503), ("http", 502), ("network", 502)])
def test_provider_errors_are_sanitized(api, kind, status):
    client, create = api
    request = httpx.Request("POST", "https://example.invalid")
    response = httpx.Response(429 if kind == "rate" else 500, request=request)
    error = {
        "timeout": lambda: APITimeoutError(request=request),
        "rate": lambda: RateLimitError("secret-provider-body", response=response, body=None),
        "http": lambda: APIStatusError("secret-provider-body", response=response, body=None),
        "network": lambda: APIConnectionError(request=request),
    }[kind]()
    create.side_effect = error
    result = client.post("/summarize", json={"text": "Notes"})
    assert result.status_code == status
    assert "secret-provider-body" not in result.text
