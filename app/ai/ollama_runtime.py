"""Local Ollama runtime settings and opt-in, privacy-safe timing logs.

No request text, account identifiers, restaurant names or response content is
recorded. Timing metadata comes from the documented Ollama chat response.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger("app.ai.ollama_performance")


def _keep_alive_setting() -> str:
    """Choose a bounded model retention period (0 immediately unloads)."""
    value = os.getenv("OM_AI_KEEP_ALIVE", "10m").strip().lower()
    return value if re.fullmatch(r"(?:0|[1-9]\d*[smh])", value) else "10m"


KEEP_ALIVE = _keep_alive_setting()
LOG_TIMINGS = os.getenv("OM_AI_LOG_TIMINGS", "0").strip().lower() in {
    "1", "true", "yes", "on",
}


def _seconds(data: dict, key: str) -> str:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "n/a"
    return f"{value / 1_000_000_000:.3f}s"


def _tokens(data: dict, key: str) -> str:
    value = data.get(key)
    return str(value) if type(value) is int and value >= 0 else "n/a"


def log_ollama_result(operation: str, response: dict, wall_seconds: float) -> None:
    """Log only Ollama durations/tokens when explicitly enabled.

    This is instrumentation, not a cache: reports must always re-query MySQL
    and authorization must always run for every incoming request.
    """
    if not LOG_TIMINGS:
        return
    metrics = response if isinstance(response, dict) else {}
    logger.warning(
        "Ollama %s wall=%.3fs total=%s load=%s prompt=%s generate=%s "
        "prompt_tokens=%s output_tokens=%s",
        operation,
        wall_seconds,
        _seconds(metrics, "total_duration"),
        _seconds(metrics, "load_duration"),
        _seconds(metrics, "prompt_eval_duration"),
        _seconds(metrics, "eval_duration"),
        _tokens(metrics, "prompt_eval_count"),
        _tokens(metrics, "eval_count"),
    )
