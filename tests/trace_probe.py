"""Isolated SDK instrumentation probe; all provider and intake I/O is intercepted.

The writer hook is test-only and tied to the pinned ddtrace version.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ddtrace.auto  # noqa: F401, E402
import httpx2  # noqa: E402
from ddtrace.llmobs import LLMObs  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from openai import OpenAI  # noqa: E402

from app import app, get_client  # noqa: E402

events = []
LLMObs._instance._llmobs_span_writer._enqueue = lambda event, size: events.append(event)
outputs = iter(
    [
        '{"question":"What does ATP carry?","answer":"Energy."}',
        '{"verdict":"supported","explanation":"The notes say ATP carries energy."}',
        "not valid JSON",
    ]
)


def respond(request):
    return httpx2.Response(
        200,
        json={
            "id": "test-completion",
            "object": "chat.completion",
            "created": 1,
            "model": "gemini-3.8-flash",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": next(outputs)},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


with OpenAI(
    api_key="test-only",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
) as provider:
    app.dependency_overrides[get_client] = lambda: provider
    with TestClient(app) as client:
        assert client.post("/quiz", json={"text": "ATP carries energy."}).status_code == 200
        assert client.post("/flashcards", json={"text": "ATP carries energy."}).status_code == 502
    app.dependency_overrides.clear()

LLMObs.flush()
workflows = {event["name"]: event for event in events if event["meta"]["span"]["kind"] == "workflow"}
llms = [event for event in events if event["meta"]["span"]["kind"] == "llm"]
assert set(workflows) == {"quiz", "flashcards"}, events
quiz = workflows["quiz"]
children = [event for event in llms if event["parent_id"] == quiz["span_id"]]
assert len(children) == 2, events
assert all(event["trace_id"] == quiz["trace_id"] for event in children)
assert all(event["metrics"]["total_tokens"] == 15 for event in llms)
assert workflows["flashcards"]["status"] == "error", events
assert all(event["status"] == "ok" for event in llms), events
print(
    json.dumps(
        {
            "workflow_spans": len(workflows),
            "llm_spans": len(llms),
            "quiz_children": len(children),
            "validation_error_captured": True,
        }
    )
)
LLMObs.disable()
