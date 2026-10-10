
import argparse
from pathlib import Path

from dotenv import load_dotenv


def main():
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"), override=False)
    if os.getenv("DD_LLMOBS_ENABLED", "0").lower() in {"1", "true"}:
        if (
            os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "0").lower() in {"1", "true"}
            and not os.getenv("DD_API_KEY", "").strip()
        ):
            raise SystemExit("Set DD_API_KEY in .env before enabling agentless telemetry.")
        # Same bootstrap as ddtrace-run; must execute before app/OpenAI imports.
        import ddtrace.auto  # noqa: F401

        print(
            "Datadog LLM tracing: ON "
            f"(app={os.getenv('DD_LLMOBS_ML_APP', 'study-buddy')}, "
            f"env={os.getenv('DD_ENV', 'local')}, site={os.getenv('DD_SITE', 'datadoghq.com')})",
            flush=True,
        )
    else:
        print("Datadog LLM tracing: OFF — set DD_LLMOBS_ENABLED=1 in .env to enable it.", flush=True)

    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=args.port, reload=False)


if __name__ == "__main__":
    main()
