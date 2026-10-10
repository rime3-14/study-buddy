# Experiments and evidence

Keep the project marked **Ongoing** until the experiments are actually completed.
Use synthetic data, one run at a time, and record UTC timestamps, model/version,
environment, endpoint, trace link, observed result and sample size.

## 1. Establish a baseline

Start the app and run `python scripts/smoke.py`. It makes four LLM calls across
three requests. Find each workflow in Agent/LLM Observability. Check that `quiz`
contains two sequential LLM children. Record input/output tokens and duration per
call; compare the total quiz duration with its two children. A single call per
endpoint validates plumbing, not reliability or stable latency percentiles.

## 2. Diagnose distinct failure classes

| Experiment | Expected API behavior | Where to investigate |
| --- | --- | --- |
| `python scripts/smoke.py --scenario invalid` | 422, no model call | HTTP/APM request; no LLM span is expected |
| `python scripts/smoke.py --scenario long` | One real flashcard request, still below the input cap | LLM input tokens, latency and valid/invalid output |
| Set `GEMINI_MODEL` temporarily to `study-buddy-invalid-model`, restart, send one request, then restore | Provider rejection, API 502 | Error on LLM child and workflow; this is a deliberately induced failure |
| Naturally malformed flashcard output | API 502 despite provider HTTP 200 | Successful LLM child followed by failed workflow validation |
| Quiz returns `unsupported` or `uncertain` | API 200 with negative quality verdict | Read the second call's output; transport success is not quality success |

Do not claim long/malformed input guarantees malformed model JSON. An invalid
HTTP request is not an LLM failure. Unit tests deterministically simulate malformed
responses; they do not constitute a real provider incident. If no natural failure
occurs during a small bounded trial, report that honestly rather than inventing one.

For long notes, compare one short and one long request with the same model and
prompt. Report token and latency deltas as observations, not a causal benchmark.
The script's long scenario makes one call, not an unbounded load test. Increasing
input beyond 30,000 characters should be rejected before consuming model tokens.

## 3. Prove APM correlation

Use the Agent-backed configuration from the README. For one request:

1. Find its LLM workflow by time, service and environment.
2. Follow the APM link and identify the FastAPI HTTP request and LLM children.
3. Save both links/IDs and a redacted screenshot showing their relationship.
4. Note every required setup step and any dead ends.

Hypothesis: an existing APM customer can move from an HTTP symptom to the LLM
cause without manually joining unrelated records. Agentless visibility does not
test that hypothesis. If the link is missing, investigate Agent forwarding,
sampling, service/env tags, region and time window before concluding a product gap.

## 4. Configure one monitor manually

For this low-volume learning exercise, start with an **error count**, which is
easier to interpret than a percentage based on two calls. A candidate metric
monitor query is:

```text
sum(last_5m):sum:ml_obs.span.error{ml_app:study-buddy,env:local,span_kind:workflow}.as_count() > 0
```

Confirm the metric and tags in the query editor before saving. Scope to workflow
spans so that an LLM error and its parent do not count twice as failed requests.
The [metric reference](https://docs.datadoghq.com/llm_observability/investigate/metrics/)
documents available tags; custom endpoint tags are not automatically metric tags.

Name: `Study Buddy — failed workflow (local demo)`.
Message: `Open the failed workflow, inspect the LLM child, then distinguish provider
failure from invalid output. Check recent model/config changes. See the experiment runbook.`
Do not add team notification recipients for a personal exercise. Disable no-data
notifications when the local application is expected to be off. Record the chosen
window and missing-data behavior rather than assuming recovery works automatically.

Trigger one intentional invalid-model request. Observe the alert state, restore
the model, send healthy traffic, and observe recovery after the window clears.
Record alert and recovery timestamps and the monitor link. A saved configuration
without a tested transition does not complete Phase 4. For production, revisit
volume thresholds, error rate, customer impact and notification noise.

## 5. Write the hands-on validation addendum

Use this table for each actual observation:

| Field | Fill after the experiment |
| --- | --- |
| Hypothesis | What did the case study predict? |
| Setup | Model, SDK version, Agent/agentless, site, timestamp |
| Evidence | Trace/monitor link, screenshot, number of requests |
| Observation | What actually happened? |
| Interpretation | What does it suggest, and what alternatives remain? |
| Product implication | Who is affected, and in what workflow? |
| Proposed experiment | Smallest change that would test the explanation |
| Success metric | How would improvement be measured? |
| Limit | What this experiment cannot establish |

Candidate friction to investigate: provider identification/cost through an
OpenAI-compatible endpoint; uncertainty between API key and app key; region
selection; agentless setup appearing to imply APM correlation. These are hypotheses
until supported by your trace or observed setup journey.
