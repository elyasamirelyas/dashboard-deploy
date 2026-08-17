"""
Generic record-and-replay cache for OpenRouter LLM calls, so repeated
pipeline test runs don't have to hit the real (paid, rate-limited) API
every time.

Toggle with the USE_LLM_CACHE env var (in .env):
- unset / "false" (default): behaves exactly as before - calls the real
  API - and additionally records every response under agents/llm_cache/.
- "true": replays a cached response if one exists for the exact same
  (model, messages) pair; falls back to a real call on a cache miss
  (and caches that new response), so a partially-warmed cache still works.
"""
import os
import json
import hashlib

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_cache")
USE_LLM_CACHE = os.getenv("USE_LLM_CACHE", "false").lower() == "true"


def cached_chat_completion(client, model, messages):
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = hashlib.sha256(
        json.dumps({"model": model, "messages": messages}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")

    if USE_LLM_CACHE and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            print(f"  [LLM cache hit: {key[:10]}]")
            return json.load(f)["content"]

    response = client.chat.completions.create(model=model, messages=messages)
    content = response.choices[0].message.content

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"model": model, "messages": messages, "content": content}, f, indent=2)

    return content