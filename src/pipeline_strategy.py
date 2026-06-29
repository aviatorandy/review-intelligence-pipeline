"""
Auto-selects processing strategy based on dataset size AND active model.
Batch size and timing estimates are driven by the model's speed profile
so the progress bar stays accurate regardless of which model is running.
"""
from .llm_client import get_model_profile


def get_strategy(n_reviews: int) -> dict:
    """
    Returns processing parameters for a given dataset size.

    Tiers:
      small  (<500)   — analyze all reviews
      medium (500–5k) — representative sample
      large  (>5k)    — compact sample, rely on vector search for Q&A coverage

    Batch size is set per-model so faster models get larger batches
    (better theme coverage) and slower models get smaller batches
    (shorter prompts = faster per-chunk).
    """
    profile = get_model_profile()
    model_batch = profile["batch_size"]

    if n_reviews < 500:
        return {
            "tier": "small",
            "sample_size": n_reviews,
            "batch_size": min(model_batch, n_reviews),
            "label": f"Analyzing all {n_reviews} reviews",
            "model": profile["model"],
        }
    elif n_reviews < 5000:
        sample = min(600, n_reviews)
        return {
            "tier": "medium",
            "sample_size": sample,
            "batch_size": model_batch,
            "label": f"Analyzing a representative sample of {sample} reviews",
            "model": profile["model"],
        }
    else:
        # Large dataset: cap sample, lean on vector search for full coverage
        sample = 600 if profile["model"] == "claude" else 400
        return {
            "tier": "large",
            "sample_size": sample,
            "batch_size": model_batch,
            "label": f"Analyzing {sample} representative reviews from your {n_reviews:,} total",
            "model": profile["model"],
        }


def estimate_time_minutes(n_reviews: int, batch_size: int, sec_per_batch: float | None = None) -> str:
    if sec_per_batch is None:
        sec_per_batch = get_model_profile()["sec_per_batch"]
    n_batches = max(1, -(-n_reviews // batch_size))  # ceiling division
    total_sec = n_batches * sec_per_batch
    if total_sec < 60:
        return "under 1 minute"
    elif total_sec < 90:
        return "about 1 minute"
    elif total_sec < 300:
        return f"about {int(total_sec // 60) + 1} minutes"
    else:
        return f"{int(total_sec // 60)}–{int(total_sec // 60) + 2} minutes"
