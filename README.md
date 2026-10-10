# Study Buddy

A deliberately small FastAPI API for testing Datadog APM and LLM Observability
(shown as **Agent Observability** in the supplied dashboard). 

The provider is **Google Gemini via the OpenAI-compatible API**, using the
`openai` Python SDK. This project does not import `google-generativeai` or
`google-genai`. Its automatic Datadog integration is therefore `openai`.

## Endpoints

All three POST endpoints accept `{"text": "Your study notes"}`.

| Endpoint | Behavior | Model calls |
| --- | --- | --- |
| `/summarize` | Requests a three-sentence summary | 1 |
| `/flashcards` | Validates JSON containing exactly five nonempty Q&A cards | 1 |
| `/quiz` | Generates a question and answer, then checks both against the original notes | 2 |

`GET /` is a liveness check. `/docs` provides interactive API documentation.
Input is limited to 30,000 characters; this is not a token limit. Blank/invalid
input returns 422 before a model call. Invalid model output returns 502, provider
timeouts 504, and provider rate limits 503. Calls have a 30-second SDK timeout and
no automatic retries; the quiz makes two sequential calls. Output is capped at
2,048 tokens per call; truncation is treated as a failure.

The flashcard response is now `{"flashcards": [...]}`, replacing the previous
`flashcards_raw` string. Quiz responses contain `question`, `answer`, and a
structured `self_check` with `verdict` and `explanation`. A negative or uncertain
verdict is a quality signal, not a transport error. Schema checks do **not** prove
factual correctness, and asking the same model to check itself is not an
independent evaluation or a Datadog native evaluator.

## Local setup (Python 3.11)

PowerShell, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# Only for a new checkout; do not overwrite an existing .env with your keys.
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. `GEMINI_MODEL` is configurable; the default is
`gemini-3.8-flash`. Availability and quota still depend on the provider account.
The example configuration starts with telemetry disabled.

```powershell
.\.venv\Scripts\python.exe run.py
```

Visit <http://127.0.0.1:8000/docs>. In a second terminal:

```powershell
.\.venv\Scripts\python.exe scripts/smoke.py
```

If another server already uses port 8000, stop it yourself or use `run.py --port 8001`
with `scripts/smoke.py --base-url http://127.0.0.1:8001`. Restart any older running
instance to load the audited code; the launcher intentionally does not auto-reload.

This sends three requests / four real model calls using synthetic biology notes.
On macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

`run.py` loads `.env` **before** importing Datadog, OpenAI, or FastAPI. Existing
shell variables take precedence. With telemetry enabled, it uses `ddtrace.auto`,
the bootstrap also used by `ddtrace-run`. Do not wrap `run.py` in `ddtrace-run`:
that would initialize tracing before `.env` is loaded. No reload subprocess is used.

## Datadog: choose what you are validating

The screenshot's URL is `us5.datadoghq.com`, so the matching site is
`DD_SITE=us5.datadoghq.com`, **not** EU or US1.

### LLM visibility without a Datadog Agent

Edit `.env`, then restart `run.py`:

```dotenv
DD_LLMOBS_ENABLED=1
DD_LLMOBS_AGENTLESS_ENABLED=1
DD_APM_TRACING_ENABLED=0
DD_LLMOBS_ML_APP=study-buddy
DD_API_KEY=your-local-api-key
DD_SITE=us5.datadoghq.com
DD_SERVICE=study-buddy
DD_ENV=local
```

The SDK sends LLM data directly to Datadog. APM is explicitly disabled in this
standalone configuration, so it does **not** demonstrate APM correlation.
The installed SDK also contains an agentless APM export path when APM is enabled;
do not infer correlation from the agentless flag alone. A successful intake response also does not prove the spans are
searchable in the dashboard; verify ingestion in the UI separately.

Alternatively, with the virtual environment activated, load the same settings
before the command-line bootstrap:

```powershell
python -m dotenv -f .env run -- ddtrace-run python -m uvicorn app:app
```

### APM + LLM correlation (the case study's central experiment)

Install and configure a supported Datadog Agent for your platform, with its API
key, US5 site, APM enabled, and LLM Observability forwarding enabled as required
by the current [Datadog setup guide](https://docs.datadoghq.com/llm_observability/setup/).
Confirm the Agent is healthy before changing the application configuration:

```dotenv
DD_LLMOBS_ENABLED=1
DD_LLMOBS_AGENTLESS_ENABLED=0
DD_APM_TRACING_ENABLED=1
DD_TRACE_AGENT_URL=http://127.0.0.1:8126
```

Restart the app. Send a request, find its workflow under `study-buddy`, and follow
the APM link to the corresponding FastAPI request. Save the trace IDs and a
redacted screenshot. A populated LLM dashboard alone is insufficient evidence.

### What is automatic, and what is application instrumentation?

The SDK captures the OpenAI client calls, their timing, tokens and errors.
Each endpoint additionally has a small explicit `LLMObs.workflow` span: it groups
the two quiz calls and captures validation failures after a successful provider
response. This is intentional application instrumentation, not zero-code tracing.

Provider attribution is a known caveat: in the audited `ddtrace` version, the
OpenAI integration recognizes `openai` in Google's `/openai/` URL. Verify the
provider label and cost estimate before treating the dashboard cost as accurate
Gemini billing. Keep this visible as a finding; no private SDK monkeypatch is used
in application code to hide it.

Only submit synthetic notes for this exercise: prompts and model outputs are
captured by LLM Observability. The API binds to localhost and has no authentication,
database, or rate limiter. Do not expose it publicly without adding access controls.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip check
```

The automated tests use simulated provider responses, require no keys, and send
no telemetry. GitHub Actions runs these checks on pushes and pull requests.
Direct runtime dependencies are pinned to the audited environment; this is not a
complete transitive lockfile. See [audit findings](docs/audit.md) for actual results.

For the remaining experiments and interview preparation:

- [Experiment runbook and evidence template](docs/experiments.md)
- [PM interview preparation (French)](docs/interview-prep.md)

## Publishing the first commit

The audit found an empty local `main` with no commits and an `origin` remote.
The changes are prepared locally; no commit or push is performed for you.

```powershell
git status --short
git check-ignore .env .venv __pycache__
git add .
git diff --cached --stat
git diff --cached
git commit -m "Build Study Buddy observability demo with validation and tests"
git push -u origin main
```

`.env`, environments, caches, logs and `artifacts/` are ignored. `.env.example`
contains placeholders only. Review staged files before publishing. If the remote
changes meanwhile, fetch and reconcile it; do not force-push.

## References

- [Google: Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)
- [Datadog: automatic instrumentation](https://docs.datadoghq.com/llm_observability/instrument/auto_instrumentation/)
- [Datadog: SDK configuration](https://docs.datadoghq.com/llm_observability/instrument/sdk/)
- [Datadog: sites](https://docs.datadoghq.com/getting_started/site/)
