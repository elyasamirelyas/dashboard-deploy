# llm_cache.py - a simple record-and-replay cache for LLM calls, so
# re-running the pipeline while testing doesn't burn real API credits
# every single time.
#
# Controlled by the USE_LLM_CACHE env var (in .env):
# - unset / "false" (the default): works exactly like a normal API call -
#   every response still gets recorded to agents/llm_cache/ along the way,
#   it's just not read back
# - "true": before calling the API, check if we've already got a cached
#   response for this exact (model, messages) pair and reuse it. if not,
#   fall back to a real call and cache that new response - so the cache
#   builds itself up over time, even if it starts out empty

import os
import json
import hashlib

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_cache")
USE_LLM_CACHE = os.getenv("USE_LLM_CACHE", "false").lower() == "true"


def cached_chat_completion(client, model, messages):
    os.makedirs(CACHE_DIR, exist_ok=True)

    # the cache key is just a hash of the model + the full message list,
    # so the same prompt always maps to the same cache file
    key = hashlib.sha256(
        json.dumps({"model": model, "messages": messages}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")

    if USE_LLM_CACHE and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            print(f"  [LLM cache hit: {key[:10]}]")
            return json.load(f)["content"]

    # cache miss (or caching's turned off) - make the real call
    response = client.chat.completions.create(model=model, messages=messages)
    content = response.choices[0].message.content

    # save it either way, so the cache keeps building up even when
    # USE_LLM_CACHE is off
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"model": model, "messages": messages, "content": content}, f, indent=2)

    return content