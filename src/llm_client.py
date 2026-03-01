import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "mistral:latest"

def call_llm(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ]
    }

    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["message"]["content"]