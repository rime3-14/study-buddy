# Audit — 2026-10-03

## Outcome

The repository is prepared for a first commit, with endpoint validation, controlled
provider errors, Datadog workflow spans, tests, CI and reproducible setup instructions.
It is **not yet fully validated end to end**: the real quiz self-check hit quota,
dashboard inspection and APM correlation remain unverified, and no monitor was created.

## Findings and changes

| Finding in original project | Change / consequence |
| --- | --- |
| No `.gitignore`; virtual environment and bytecode appeared as untracked files | Ignore environments, local secrets, caches, logs and audit artifacts |
| README/example requested `OPENAI_API_KEY`; app required `GEMINI_API_KEY` | Consistent `.env.example`, correct provider description and startup loader |
| `ddtrace` installed locally but absent from requirements | Pin audited direct runtime dependencies, include tracing and dotenv |
| Client construction failed at import if the key was missing | Lazy client dependency; health/docs remain usable; model endpoints return 503 |
| Unrestricted/blank input and unbounded default retry behavior | 30,000-character cap, nonempty input, 30-second SDK timeout, zero retries, output cap |
| Flashcards returned an unchecked string | Parse JSON, require five cards and nonempty fields; malformed output becomes an observable workflow error |
| Quiz answered a question without the source notes or a proposed answer | Generate question + answer, then compare against the original notes in a second call |
| No workflow parent for the chained operation | Explicit workflow spans group calls and expose post-generation validation failures |
| No automated checks | Contract tests, real SDK instrumentation probe with intercepted I/O, lint and GitHub Actions |

Validation intentionally checks structure, not the semantic correctness of cards.
Prompts remain fallible. No fabricated incident is added to the production endpoints.

## Verification actually performed

- Python 3.11.9, FastAPI 0.142.2, OpenAI SDK 3.22.1, ddtrace 4.15.4.
- **38 automated tests passed**. The isolated tracing test uses the real OpenAI
  client with a simulated HTTP response and intercepted Datadog output. It verifies
  two quiz children in the same trace, token metrics, and a failed validation workflow
  with a successful LLM child. This is local instrumentation evidence, not ingestion.
- Ruff passed; `pip check` found no broken dependencies.
- `run.py` startup verified in a separate Uvicorn process on a temporary port:
  real HTTP health check, OpenAPI routes and 422 input rejection passed. An existing
  process was already listening on port 8000 and was left running unchanged.
- `.env`, `.venv`, `__pycache__` and `artifacts/` verified ignored by Git.
- Real Gemini/Datadog key values checked against publishable files: no matches.
- Local `main` had no commits; `origin` was configured and `git ls-remote --heads`
  returned no branches. No commit or push was made during the audit.

## Live calls and Datadog intake

Synthetic biology notes were sent through FastAPI's in-process HTTP test client
to the **real Gemini API**. No simulated model responses were used in these runs.
The model was `gemini-3.8-flash`.

Two initial three-endpoint runs produced provider 503s on summarize and quiz,
while flashcards succeeded. A later run explicitly disabled APM tracing to verify
the standalone LLM export path:

| Endpoint | API status | Approx. duration | Observed outcome |
| --- | --- | --- | --- |
| `/summarize` | 200 | 4.41 s | Summary returned; 59 input + 45 output tokens |
| `/flashcards` | 200 | 4.53 s | Five validated cards; 97 input + 111 output tokens |
| `/quiz` | 503 | 4.19 s | First call succeeded (82 + 19 tokens); second call received provider 429 |

These are individual observations, not benchmarks. The change in provider outcomes
between runs is not evidence that the export setting caused the change.

The final run used `DD_ENV=audit`, `DD_SITE=us5.datadoghq.com`,
`DD_LLMOBS_AGENTLESS_ENABLED=1`, and `DD_APM_TRACING_ENABLED=0`. The Datadog intake
returned **202 for all three batches (2 + 2 + 3 = 7 spans)**. This verifies accepted
export, not indexing, UI availability, or APM correlation.

The quiz workflow contained two LLM children with the same trace ID; its second
child and parent were marked as errors. Thus a real provider failure was captured.
It has not yet been diagnosed through the Datadog UI, as required by Phase 3.
The available browser required sign-in; the user chose to defer dashboard verification.
Raw local evidence is in ignored `artifacts/live-results.json`; keep trace IDs and
account-specific evidence out of the public repository unless deliberately reviewed.

## Confirmed friction: SDK/provider attribution

Captured spans report `model_name=gemini-3.8-flash` and `model_provider=openai`.
The installed integration's provider detection matches `openai` inside Google's
compatibility URL. This is a concrete attribution issue in this setup. It does
**not** establish that every Gemini integration behaves this way, nor that the
displayed cost is necessarily wrong. Reconcile any cost estimate before using it
as a billing claim. A future comparison with the native Google SDK would be useful.

## Export-mode nuance

The supplied setup advice describes agentless mode as LLM-only. The installed SDK
also implements an `APM_AGENTLESS` path when APM tracing is enabled. The example now
sets `DD_APM_TRACING_ENABLED=0` explicitly to make the standalone experiment clear.
The Agent-backed instructions set it to `1`. Neither route's APM correlation was
verified in the dashboard during this audit; avoid categorical claims based only
on `DD_LLMOBS_AGENTLESS_ENABLED`.

## Roadmap status supported by evidence

| Phase | Status |
| --- | --- |
| 1 — app | Implementation + offline verification complete; real summary/flashcards succeed; successful real quiz still to verify after quota recovers |
| 2 — instrumentation | Local span structure and LLM intake verified; all-endpoint dashboard visibility and APM correlation pending |
| 3 — diagnose failure | Real provider errors captured; UI-led diagnosis and long-input experiment pending |
| 4 — monitor | Runbook prepared; monitor creation, trigger and recovery not performed |
| 5 — findings | Audit observations recorded; case-study addendum awaits remaining hands-on evidence |

The initial user screenshot shows two LLM calls, 50% error rate, 444 tokens and
6.26 s p95. It establishes some prior ingestion; it does not establish a reliable
error rate, endpoint coverage or the cause of the failed call.
