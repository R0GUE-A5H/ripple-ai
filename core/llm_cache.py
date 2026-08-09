"""
Cache/replay layer for Groq LLM calls used by Ripple AI's repair agent.

Modes (driven entirely by core.config.DEMO_MODE, i.e. the DEMO_MODE env var):

  DEMO_MODE=true (default)
      Never calls Groq. Always replays from demo/cached_llm_responses.json.
      No GROQ_API_KEY required. This is the judge-facing path.

  DEMO_MODE=false, RECORD_CACHE=true
      Calls Groq for real AND writes the response into the cache file,
      keyed by cache_key. Run this once against your live GROQ_API_KEY,
      for the exact demo scenario (the nyc_taxi_pipeline staging_trips
      freshness breach), BEFORE packaging the docker image — that's what
      populates demo/cached_llm_responses.json so demo mode has something
      to replay.

  DEMO_MODE=false, RECORD_CACHE=false (default live behavior)
      Calls Groq for real, ignores the cache file entirely.

cache_key identifies the *scenario*, not the raw prompt text — e.g.
"generate_repair:staging_trips". The demo dataset is fixed, so the right
answer doesn't change even if prompt formatting shifts slightly between
runs. Hashing the full prompt (as a naive cache would) is fragile for
exactly that reason.
"""

import json
import os
from pathlib import Path

from core.config import DEMO_MODE

CACHE_PATH = (
    Path(__file__).resolve().parent.parent / "demo" / "cached_llm_responses.json"
)
RECORD_CACHE = os.getenv("RECORD_CACHE", "false").lower() == "true"


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def llm_call(llm, messages, cache_key: str) -> str:
    if DEMO_MODE:
        cache = _load_cache()
        if cache_key not in cache:
            raise RuntimeError(
                f"[JUDGE MODE] No cached LLM response for '{cache_key}'. "
                f"Run once with DEMO_MODE=false and RECORD_CACHE=true against "
                f"a real GROQ_API_KEY to populate {CACHE_PATH} before "
                f"packaging the demo."
            )
        print(f"[JUDGE MODE] Serving cached LLM response for '{cache_key}'")
        return cache[cache_key]

    # Live mode: real call.
    response = llm.invoke(messages)
    content = response.content.strip()

    if RECORD_CACHE:
        cache = _load_cache()
        cache[cache_key] = content
        _save_cache(cache)
        print(f"[RECORD] Cached LLM response for '{cache_key}' -> {CACHE_PATH}")

    return content
