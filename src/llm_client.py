import os
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral:latest"
CLAUDE_MODEL = "claude-opus-4-8"


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
    payload = {
        "model": OLLAMA_MODEL,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["message"]["content"]


def call_llm(system_prompt: str, user_prompt: str) -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_claude(system_prompt, user_prompt)
    return _call_ollama(system_prompt, user_prompt)