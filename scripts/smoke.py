"""Exercise a running API with synthetic notes. Four model calls for baseline."""

import argparse
import json
import time
import urllib.error
import urllib.request

NOTES = (
    "Photosynthesis converts light energy into chemical energy. Chlorophyll absorbs light. "
    "Plants use carbon dioxide and water to produce glucose and oxygen. "
    "Chloroplasts contain chlorophyll. Cellular respiration releases energy from glucose. "
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["baseline", "long", "invalid"], default="baseline")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    notes = NOTES if args.scenario == "baseline" else NOTES * 80
    endpoints = ["summarize", "flashcards", "quiz"] if args.scenario == "baseline" else ["flashcards"]
    if args.scenario == "invalid":
        notes = " "
    failed = False
    for endpoint in endpoints:
        request = urllib.request.Request(
            f"{args.base_url.rstrip('/')}/{endpoint}",
            data=json.dumps({"text": notes}).encode(),
            headers={"Content-Type": "application/json"},
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=75) as response:
                status, body = response.status, response.read().decode()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read().decode()
        except urllib.error.URLError:
            print("Cannot reach the local API. Start python run.py first.")
            raise SystemExit(1)
        expected = 422 if args.scenario == "invalid" else 200
        failed |= status != expected
        print(
            json.dumps(
                {
                    "endpoint": endpoint,
                    "status": status,
                    "seconds": round(time.monotonic() - started, 2),
                    "response": json.loads(body),
                }
            )
        )
    raise SystemExit(int(failed))


if __name__ == "__main__":
    main()
