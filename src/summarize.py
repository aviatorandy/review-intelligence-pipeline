import json
from pathlib import Path
from .llm_client import call_llm


def load_prompt(path: str) -> str:
    return Path(path).read_text()


def format_reviews_jsonl(rows):
    return "\n".join([
        json.dumps({
            "review_id": r["review_id"],
            "label": int(r["label"]),
            "sentiment": "POSITIVE" if int(r["label"]) == 1 else "NEGATIVE",
            "text": r["text"]
        })
        for r in rows
    ])


def run_summary(rows):
    system_prompt = load_prompt("prompts/system.md")
    task_prompt = load_prompt("prompts/summarize_v1.md")

    reviews_jsonl = format_reviews_jsonl(rows)
    user_prompt = task_prompt.replace("{{REVIEWS_JSONL}}", reviews_jsonl)

    return call_llm(system_prompt, user_prompt)
