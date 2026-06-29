"""
Auto-selects processing strategy based on dataset size.
No user-facing configuration needed.
"""


def get_strategy(n_reviews: int) -> dict:
    """
    Returns processing parameters for a given dataset size.

    Tiers:
      small  (<500)   — analyze all reviews directly
      medium (500–5k) — sample intelligently, focus on signal
      large  (>5k)    — sample for summarization, use vector search for Q&A
    """
    if n_reviews < 500:
        return {
            "tier": "small",
            "sample_size": n_reviews,
            "batch_size": 40,
            "label": f"Analyzing all {n_reviews} reviews",
        }
    elif n_reviews < 5000:
        sample = min(600, n_reviews)
        return {
            "tier": "medium",
            "sample_size": sample,
            "batch_size": 50,
            "label": f"Analyzing a representative sample of {sample} reviews",
        }
    else:
        sample = 400
        return {
            "tier": "large",
            "sample_size": sample,
            "batch_size": 50,
            "label": f"Analyzing {sample} representative reviews from your {n_reviews:,} total",
        }


def estimate_time_minutes(n_reviews: int, batch_size: int, sec_per_batch: float = 60) -> str:
    n_batches = max(1, n_reviews // batch_size)
    total_sec = n_batches * sec_per_batch
    if total_sec < 90:
        return "under 2 minutes"
    elif total_sec < 300:
        return f"about {int(total_sec // 60) + 1} minutes"
    else:
        return f"{int(total_sec // 60)}–{int(total_sec // 60) + 2} minutes"
