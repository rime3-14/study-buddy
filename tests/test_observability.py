"""Verify real SDK spans in a fresh process, without external network calls."""

import os
import subprocess
import sys
from pathlib import Path


def test_sdk_traces_quiz_and_validation_failure():
    env = {key: value for key, value in os.environ.items() if not key.startswith("DD_")}
    env.update(
        {
            "DD_LLMOBS_ENABLED": "1",
            "DD_LLMOBS_AGENTLESS_ENABLED": "1",
            "DD_APM_TRACING_ENABLED": "0",
            "DD_LLMOBS_ML_APP": "study-buddy-test",
            "DD_API_KEY": "test-only",
            "DD_INSTRUMENTATION_TELEMETRY_ENABLED": "0",
            "DD_REMOTE_CONFIGURATION_ENABLED": "0",
        }
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("trace_probe.py"))],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
