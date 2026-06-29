"""
LLM client — auto-selects Claude API (if ANTHROPIC_API_KEY set) or local Ollama.

Ollama model preference order (fastest → most capable):
  phi3:mini  → ~3x faster than mistral, good JSON output, 4k context
  mistral    → fallback if phi3 not pulled

Set OLLAMA_MODEL env var to override, e.g. OLLAMA_MODEL=llama3:8b
"""
import os
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
CLAUDE_MODEL = "claude-opus-4-8"

# Model capability profile — drives batch size decisions in pipeline_strategy.py
_MODEL_PROFILES = {
    "phi3:mini":       {"ctx": 4096,  "sec_per_batch": 20, "batch_size": 30},
    "phi3:medium":     {"ctx": 8192,  "sec_per_batch": 40, "batch_size": 40},
    "mistral:latest":  {"ctx": 8192,  "sec_per_batch": 60, "batch_size": 40},
    "mistral:7b":      {"ctx": 8192,  "sec_per_batch": 60, "batch_size": 40},
    "llama3:8b":       {"ctx": 8192,  "sec_per_batch": 45, "batch_size": 40},
    "llama3:70b":      {"ctx": 8192,  "sec_per_batch": 120, "batch_size": 50},
    "claude":          {"ctx": 200000, "sec_per_batch": 8,  "batch_size": 80},
}
_DEFAULT_PROFILE = {"ctx": 8192, "sec_per_batch": 60, "batch_size": 40}


def get_active_model() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return os.environ.get("OLLAMA_MODEL", _detect_ollama_model())


def get_model_profile() -> dict:
    model = get_active_model()
    for key, profile in _MODEL_PROFILES.items():
        if model.startswith(key.split(":")[0]) and (
            ":" not in key or model == key
        ):
            return {**profile, "model": model}
    return {**_DEFAULT_PROFILE, "model": model}


def _detect_ollama_model() -> str:
    """Check which models are pulled locally; prefer phi3:mini for speed."""
    preference = ["phi3:mini", "phi3:medium", "mistral:latest", "mistral:7b", "llama3:8b"]
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.ok:
            pulled = {m["name"] for m in resp.json().get("models", [])}
            for model in preference:
                if model in pulled:
                    return model
            # Fall back to first available model
            if pulled:
                return next(iter(pulled))
    except Exception:
        pass
    return "mistral:latest"


def _call_claude(system_prompt: str, user_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0.2,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    model = get_active_model()
    profile = get_model_profile()
    ctx = profile["ctx"]

    payload = {
        "model": model,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1,   # lower = more consistent JSON
            "num_ctx": ctx,
            "num_predict": 2048,  # cap output tokens for speed
            "repeat_penalty": 1.1,
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()
    return response.json()["message"]["content"]


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_claude(system_prompt, user_prompt)
    return _call_ollama(system_prompt, user_prompt)
