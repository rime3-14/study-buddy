# Study Buddy

A small FastAPI app that sends study notes to Gemini and optionally traces the
calls with Datadog. No database, accounts, or frontend framework.

## Start

From the project folder:

```powershell
.\.venv\Scripts\python.exe run.py --port 8001
```

Open **http://127.0.0.1:8001/docs**. Expand an endpoint, replace the example text
with your notes, and click **Execute**.

| Endpoint | Result | Model calls |
| --- | --- | --- |
| `/summarize` | A short summary | 1 |
| `/flashcards` | Five question-and-answer cards | 1 |
| `/quiz` | A question, answer, and check against the notes | 2 |

Stop with **Ctrl+C**. Restart after changing code or `.env`.

## First-time setup

Requires Python 3.11. Skip this if your environment is already installed.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` and your chosen `GEMINI_MODEL` in `.env`. Do not overwrite
an existing `.env` containing your keys. Shell variables override `.env` values.

For Datadog, set `DD_LLMOBS_ENABLED=1`, `DD_API_KEY`, and the correct `DD_SITE`
(US5 here: `us5.datadoghq.com`). The terminal reports whether tracing is on.
The example uses standalone LLM tracing with APM disabled.

## Code

- `app.py`: three endpoints, validation, provider errors, and Datadog workflows.
- `run.py`: loads `.env`, initializes tracing, and starts the server.
- `requirements.txt`: runtime libraries.
- `.env`: private settings; excluded from Git by `.gitignore`.

The OpenAI SDK calls Gemini's compatible API. Each request gets a client that
closes afterwards; the quiz shares that client for both calls. Datadog groups
calls under the endpoint's workflow.

Inputs must contain 1–30,000 characters. Calls have a 30-second timeout and no
automatic retries. Invalid JSON from the model returns 502; provider timeouts
return 504 and quota errors 503. A quiz self-check is not a guarantee of accuracy.
Use synthetic notes when tracing: prompts and answers are sent to Datadog.
