"""
Full pipeline: processes all reviews in chunks, aggregates themes, writes final report.

Usage:
    python -m src.full_pipeline --data "data/angrybirds amazon reviews.csv"
    python -m src.full_pipeline --data "data/angrybirds amazon reviews.csv" --max-reviews 500
    python -m src.full_pipeline --data "data/angrybirds amazon reviews.csv" --run-dir results/runs/20260226_140000_full

Options:
    --chunk-size    Reviews per chunk (default: 50)
    --max-reviews   Limit total reviews processed (default: all)
    --run-dir       Resume a previous run by passing its directory
"""
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from .ingest import load_reviews
from .summarize import run_summary
from .validators import validate_json_schema
from .report_printer import print_report
from .report_html import generate_html


# ─── Progress bar ────────────────────────────────────────────────────────────

import re

_NEGATIVE_SIGNALS = re.compile(
    r"\b(bad|terrible|awful|hate|hated|worst|broken|crash(es|ing|ed)?|bug(gy|s)?|"
    r"useless|disappoint(ing|ed|ment)?|annoy(ing|ed)?|frustrat(ing|ed|ion)?|"
    r"problem(s)?|issue(s)?|doesn.t work|won.t|slow|lag(gy)?|freez(e|ing|es)?|"
    r"ruin(s|ed)?|terrible|horrible|waste|scam|fake|mislead|glitch(y|es)?|"
    r"uninstall|remove(d)?|not worth|never again|poor|keep(s)? crash|stopped working|"
    r"can.t|cannot|no longer|used to|unfortunately|unfortunately)\b",
    re.IGNORECASE,
)


def build_chunks(rows: list, batch_size: int) -> list[list]:
    """
    Build chunks from rows.

    If rows are enriched (have 'topic' field): group by topic so each chunk
    gives the LLM focused, coherent signal. Within each topic, sort negatives
    first (severity: high → medium → low) so complaints surface clearly.
    Small topic groups (<5 reviews) are merged into an 'other' bucket to avoid
    tiny noisy chunks.

    Falls back to sequential chunking for plain (non-enriched) CSVs.
    """
    if not rows or "topic" not in rows[0]:
        # Plain CSV — sequential chunks + negative chunk
        chunks = [rows[i:i + batch_size] for i in range(0, len(rows), batch_size)]
        negatives = _text_verified_negatives(rows)
        if len(negatives) >= 5:
            chunks.append(negatives)
        return chunks

    # ── Enriched path: group by topic ─────────────────────────────────────────
    _SEV_ORDER = {"high": 0, "medium": 1, "low": 2}

    from collections import defaultdict
    buckets: dict[str, list] = defaultdict(list)
    for row in rows:
        buckets[row.get("topic", "general")].append(row)

    # Merge small topic groups into 'other'
    merged_other = list(buckets.pop("other", []))
    for topic in list(buckets.keys()):
        if len(buckets[topic]) < 5:
            merged_other.extend(buckets.pop(topic))
    if merged_other:
        buckets["other"] = merged_other

    chunks = []
    for topic, topic_rows in buckets.items():
        # Sort: negatives first, then by severity
        topic_rows.sort(key=lambda r: (
            0 if r.get("sentiment_text") == "negative" else 1,
            _SEV_ORDER.get(r.get("severity", "low"), 2),
        ))
        # Split into batch_size chunks
        for i in range(0, len(topic_rows), batch_size):
            chunks.append(topic_rows[i:i + batch_size])

    # Dedicated negative chunk using text-verified negatives (catches any missed)
    if "sentiment_text" in rows[0]:
        # Enriched: use sentiment_text field instead of regex scan
        negatives = [r for r in rows if r.get("sentiment_text") == "negative"]
    else:
        negatives = _text_verified_negatives(rows)

    if len(negatives) >= 5:
        negatives.sort(key=lambda r: _SEV_ORDER.get(r.get("severity", "low"), 2))
        chunks.append(negatives)

    return chunks


def _text_verified_negatives(rows: list) -> list:
    """
    Return label=0 rows where the review text itself contains negative language.
    Filters out mislabeled reviews (positive text, wrong label) that would otherwise
    cause the LLM to hallucinate complaint themes.
    """
    return [
        r for r in rows
        if int(r.get("label", 1)) == 0 and bool(_NEGATIVE_SIGNALS.search(r.get("text", "")))
    ]


def progress_bar(current, total, start_time, width=40):
    pct = current / total
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    elapsed = time.time() - start_time
    eta = (elapsed / current * (total - current)) if current > 0 else 0
    eta_str = f"{int(eta//60)}m{int(eta%60):02d}s" if eta > 60 else f"{int(eta)}s"
    print(f"\r  [{bar}] {current}/{total} chunks  {pct*100:.1f}%  ETA {eta_str}   ", end="", flush=True)


# ─── Chunk processing ─────────────────────────────────────────────────────────

def process_chunk(chunk_rows, chunk_id, chunks_dir):
    """Process one chunk. Returns parsed obj or None on failure."""
    chunk_file = chunks_dir / f"chunk_{chunk_id:04d}.json"

    # Skip if already done
    if chunk_file.exists():
        with open(chunk_file) as f:
            return json.load(f)

    try:
        output_str = run_summary(chunk_rows)
        valid, obj, err = validate_json_schema(output_str, "evals/schema.json")
        if not valid:
            (chunks_dir / f"chunk_{chunk_id:04d}_error.txt").write_text(
                f"Error: {err}\n\nRaw output:\n{output_str}"
            )
            return None

        with open(chunk_file, "w") as f:
            json.dump(obj, f)
        return obj

    except Exception as e:
        (chunks_dir / f"chunk_{chunk_id:04d}_error.txt").write_text(str(e))
        return None


# ─── Aggregation ──────────────────────────────────────────────────────────────

FUZZY_THRESHOLD = 70

# Semantic groups — themes sharing ANY keyword in a group get merged
# Catches "wide appeal" vs "universal appeal" vs "widespread appeal"
SEMANTIC_GROUPS = [
    {"appeal", "popular", "popularity", "widespread", "universal", "everyone", "all ages", "family"},
    {"addictive", "addictiveness", "addicting", "addicted", "hooked", "cant stop", "keep using"},
    {"fun", "enjoyable", "enjoyability", "entertaining", "entertainment", "great app", "great game"},
    {"ads", "advertisement", "ad-free", "pop-up", "popup", "intrusive ads", "annoying ads"},
    {"crash", "crashes", "force close", "freeze", "bug", "technical", "compatibility"},
    {"free", "no cost", "price", "paid", "premium"},
    {"levels", "level design", "mechanics", "challenging", "difficulty"},
    {"kids", "children", "family friendly", "age groups", "educational", "education", "learning"},
    {"offline", "online only", "requires internet", "connectivity", "no wifi", "internet required", "sign in"},
]


def normalize(text):
    return text.lower().strip()


def get_semantic_group(theme):
    norm = normalize(theme)
    for i, group in enumerate(SEMANTIC_GROUPS):
        if any(kw in norm for kw in group):
            return i
    return None


def find_fuzzy_key(new_theme, existing_keys, threshold=FUZZY_THRESHOLD):
    """
    Two strategies:
    1. Semantic group — catches conceptually identical themes with different words
    2. Fuzzy string — catches near-identical phrasings
    """
    norm_new = normalize(new_theme)
    new_group = get_semantic_group(new_theme)

    # Strategy 1: semantic group match
    if new_group is not None:
        for key in existing_keys:
            if get_semantic_group(key) == new_group:
                return key

    # Strategy 2: fuzzy string match
    try:
        from rapidfuzz import fuzz
        best_score = 0
        best_key = None
        for key in existing_keys:
            score = fuzz.token_sort_ratio(norm_new, key)
            if score > best_score:
                best_score = score
                best_key = key
        return best_key if best_score >= threshold else None
    except ImportError:
        return norm_new if norm_new in existing_keys else None


def merge_into(bucket, item, max_evidence=3):
    """Add a theme item's count and evidence into an existing bucket."""
    bucket["review_count"] += item.get("review_count", 1)
    existing_quotes = {e["quote"] for e in bucket["evidence"]}
    for ev in item.get("evidence", []):
        if ev["quote"] not in existing_quotes and len(bucket["evidence"]) < max_evidence:
            bucket["evidence"].append(ev)
            existing_quotes.add(ev["quote"])
    # Upgrade confidence based on accumulated count
    if bucket["review_count"] >= 10:
        bucket["confidence"] = "high"
    elif bucket["review_count"] >= 5:
        bucket["confidence"] = "medium"


def aggregate_themes(theme_list, buckets):
    """Merge a list of themes into the buckets dict using fuzzy matching."""
    for item in theme_list:
        norm = normalize(item["theme"])
        match = find_fuzzy_key(item["theme"], buckets.keys())

        if match:
            # Merge into existing similar theme
            merge_into(buckets[match], item)
        else:
            # New theme — add it
            buckets[norm] = {
                "theme": item["theme"],  # keep the first seen version of the name
                "review_count": item.get("review_count", 1),
                "confidence": item.get("confidence", "low"),
                "evidence": list(item.get("evidence", []))[:3]
            }


def aggregate_chunks(chunk_results):
    """
    Merge themes across all chunks using fuzzy matching.
    Similar themes (e.g. 'addictiveness' vs 'Addictive') are merged automatically.
    review_counts are summed. Evidence is collected (up to 3 per theme).
    """
    strengths = {}
    complaints = {}
    all_bullets = []

    for obj in chunk_results:
        if obj is None:
            continue

        for b in obj.get("summary_bullets", []):
            all_bullets.append(b)

        aggregate_themes(obj.get("top_strengths", []), strengths)
        aggregate_themes(obj.get("top_complaints", []), complaints)

    def recompute_confidence(themes):
        for t in themes:
            if t["review_count"] >= 10:
                t["confidence"] = "high"
            elif t["review_count"] >= 5:
                t["confidence"] = "medium"
            else:
                t["confidence"] = "low"
        return themes

    top_strengths = recompute_confidence(
        sorted(strengths.values(), key=lambda x: x["review_count"], reverse=True)[:5]
    )
    top_complaints = recompute_confidence(
        sorted(complaints.values(), key=lambda x: x["review_count"], reverse=True)[:5]
    )

    # Deduplicate bullets by fuzzy similarity too
    deduped_bullets = []
    seen_claims = []
    for b in all_bullets:
        match = find_fuzzy_key(b["claim"], [normalize(c) for c in seen_claims], threshold=85)
        if not match:
            seen_claims.append(b["claim"])
            deduped_bullets.append(b)
    summary_bullets = deduped_bullets[:6]

    return top_strengths, top_complaints, summary_bullets


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to reviews CSV")
    parser.add_argument("--chunk-size", type=int, default=50, help="Reviews per chunk (default: 50)")
    parser.add_argument("--max-reviews", type=int, default=None, help="Limit total reviews processed (default: all)")
    parser.add_argument("--run-dir", type=str, default=None, help="Resume a previous run")
    args = parser.parse_args()

    # Set up run directory
    if args.run_dir:
        run_dir = Path(args.run_dir)
        print(f"Resuming run at: {run_dir}")
    else:
        run_dir = Path(f"results/runs/{datetime.now().strftime('%Y%m%d_%H%M%S')}_full")
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"New run at: {run_dir}")

    chunks_dir = run_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # Load data
    print(f"\nLoading reviews from {args.data}...")
    df = load_reviews(args.data)

    # Random sample if max-reviews set, otherwise use full dataset
    if args.max_reviews:
        sample_n = min(args.max_reviews, len(df))
        df = df.sample(n=sample_n, random_state=42)
        print(f"Random sample of {sample_n} reviews (--max-reviews, seed=42)")

    rows = df.to_dict(orient="records")

    total = len(rows)

    # Split into chunks
    chunks = [rows[i:i + args.chunk_size] for i in range(0, total, args.chunk_size)]

    # Add a dedicated negative-only chunk using TEXT-verified negatives.
    # We filter by text content, not just label, to avoid mislabeled reviews
    # generating hallucinated complaints.
    negatives = _text_verified_negatives(rows)
    if len(negatives) >= 5:
        chunks.append(negatives)
        print(f"Adding dedicated negative chunk ({len(negatives)} text-verified negatives)")

    n_chunks = len(chunks)

    already_done = len(list(chunks_dir.glob("chunk_*.json")))
    print(f"Total reviews:  {total}")
    print(f"Chunk size:     {args.chunk_size}")
    print(f"Total chunks:   {n_chunks}")
    print(f"Already done:   {already_done}")
    print(f"Remaining:      {n_chunks - already_done}")
    print()

    # Process chunks
    start_time = time.time()
    chunk_results = []
    failed = 0

    for i, chunk_rows in enumerate(chunks):
        progress_bar(i + 1, n_chunks, start_time)
        result = process_chunk(chunk_rows, i, chunks_dir)
        if result is None:
            failed += 1
        chunk_results.append(result)

    print()
    elapsed = time.time() - start_time
    print(f"\nDone in {int(elapsed//60)}m{int(elapsed%60):02d}s")
    print(f"Chunks succeeded: {n_chunks - failed}/{n_chunks}")
    if failed > 0:
        print(f"⚠️  {failed} chunks failed — check {chunks_dir}/*_error.txt")

    # Compute ground truth sentiment
    n = len(rows)
    pos = sum(1 for r in rows if int(r["label"]) == 1)
    sentiment = {
        "positive_rate": round(pos / n, 4),
        "negative_rate": round((n - pos) / n, 4),
        "n_reviews": n
    }

    # Aggregate
    print("\nAggregating themes across all chunks...")
    top_strengths, top_complaints, summary_bullets = aggregate_chunks(chunk_results)

    final = {
        "summary_bullets": summary_bullets,
        "top_strengths": top_strengths,
        "top_complaints": top_complaints,
        "sentiment": sentiment,
        "unknowns": [],
        "meta": {
            "total_reviews": total,
            "chunks_processed": n_chunks - failed,
            "chunks_failed": failed,
            "chunk_size": args.chunk_size,
        }
    }

    # Save output.json
    output_path = run_dir / "output.json"
    with open(output_path, "w") as f:
        json.dump(final, f, indent=2)
    print(f"Saved: {output_path}")

    # Print terminal report
    print_report(final)

    # Generate HTML report
    html_path = run_dir / "report.html"
    generate_html(final, str(html_path), data_path=args.data)
    print(f"\nOpen report: open {html_path}")


if __name__ == "__main__":
    main()
