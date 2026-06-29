"""
Eval: measure LLM sentiment classification accuracy against ground truth labels.

For each review, asks the LLM: positive or negative?
Compares to the ground truth label column.
Reports accuracy, precision, recall, F1, and confusion matrix.

Usage:
    python -m evals.eval_sentiment --data data/sample/angry_birds_enriched.csv
    python -m evals.eval_sentiment --data data/sample/angry_birds_enriched.csv --sample 50
    python -m evals.eval_sentiment --data data/sample/angry_birds_enriched.csv --baseline-only
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import call_llm
from src.ingest import load_reviews

SYSTEM = "You are a sentiment classifier. Output only valid JSON. No markdown."

PROMPT = """Classify the sentiment of this customer review as 'positive' or 'negative'.

Review: {text}

Return exactly: {{"sentiment": "positive"}} or {{"sentiment": "negative"}}"""


def classify_one(text: str) -> str | None:
    try:
        raw = call_llm(SYSTEM, PROMPT.format(text=text[:500]))
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(raw)
        s = result.get("sentiment", "").lower()
        return s if s in ("positive", "negative") else None
    except Exception:
        return None


def compute_metrics(y_true: list, y_pred: list) -> dict:
    """y_true and y_pred are lists of 'positive'/'negative' strings."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == "positive" and p == "positive")
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == "negative" and p == "negative")
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == "negative" and p == "positive")
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == "positive" and p == "negative")

    accuracy = (tp + tn) / len(y_true) if y_true else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "total": len(y_true),
        "errors": sum(1 for p in y_pred if p is None),
    }


def baseline_rule_metrics(df) -> dict:
    """Accuracy of the rule-based enrichment (sentiment_text) vs ground truth."""
    if "sentiment_text" not in df.columns:
        return {}
    rows = df.to_dict(orient="records")
    y_true, y_pred = [], []
    for r in rows:
        st = r.get("sentiment_text", "mixed")
        if st == "mixed":
            continue
        y_true.append("positive" if int(r["label"]) == 1 else "negative")
        y_pred.append(st)
    return compute_metrics(y_true, y_pred)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--sample", type=int, default=None, help="Limit reviews evaluated (default: all)")
    parser.add_argument("--baseline-only", action="store_true", help="Only run rule-based baseline, skip LLM")
    parser.add_argument("--output", default=None, help="Save results JSON to this path")
    args = parser.parse_args()

    df = load_reviews(args.data)
    if args.sample:
        df = df.sample(n=min(args.sample, len(df)), random_state=42)

    print(f"\nDataset: {args.data}")
    print(f"Reviews: {len(df)} (label=1: {(df.label==1).sum()}, label=0: {(df.label==0).sum()})")

    # ── Baseline: rule-based enrichment ──────────────────────────────────────
    baseline = baseline_rule_metrics(df)
    if baseline:
        print(f"\n── Rule-based baseline (sentiment_text vs label) ──")
        print(f"  Accuracy:  {baseline['accuracy']:.1%}")
        print(f"  Precision: {baseline['precision']:.1%}")
        print(f"  Recall:    {baseline['recall']:.1%}")
        print(f"  F1:        {baseline['f1']:.1%}")
        cm = baseline["confusion"]
        print(f"  Confusion: TP={cm['tp']} TN={cm['tn']} FP={cm['fp']} FN={cm['fn']}")
        print(f"  (excludes {len(df) - baseline['total']} 'mixed' reviews)")

    if args.baseline_only:
        return

    # ── LLM eval ─────────────────────────────────────────────────────────────
    print(f"\n── LLM sentiment classification ──")
    rows = df.to_dict(orient="records")
    y_true, y_pred = [], []
    failed = 0
    start = time.time()

    for i, r in enumerate(rows):
        gt = "positive" if int(r["label"]) == 1 else "negative"
        pred = classify_one(r["text"])
        y_true.append(gt)
        y_pred.append(pred if pred else "error")

        if pred is None:
            failed += 1
        correct = "✓" if pred == gt else ("?" if pred is None else "✗")
        print(f"  [{i+1:3d}/{len(rows)}] {correct}  label={gt:<9} pred={pred or 'error':<9}  {r['text'][:60]}")

    elapsed = round(time.time() - start)
    valid_pred = [p for p in y_pred if p != "error"]
    valid_true = [t for t, p in zip(y_true, y_pred) if p != "error"]
    metrics = compute_metrics(valid_true, valid_pred)

    print(f"\n── LLM Results ({elapsed}s) ──")
    print(f"  Accuracy:  {metrics['accuracy']:.1%}")
    print(f"  Precision: {metrics['precision']:.1%}")
    print(f"  Recall:    {metrics['recall']:.1%}")
    print(f"  F1:        {metrics['f1']:.1%}")
    cm = metrics["confusion"]
    print(f"  Confusion: TP={cm['tp']} TN={cm['tn']} FP={cm['fp']} FN={cm['fn']}")
    print(f"  Errors (no JSON parse): {failed}/{len(rows)}")

    if baseline:
        delta = metrics["accuracy"] - baseline["accuracy"]
        sign = "+" if delta >= 0 else ""
        print(f"\n  vs rule-based baseline: {sign}{delta:.1%}")

    results = {
        "dataset": args.data,
        "n_reviews": len(rows),
        "llm_metrics": metrics,
        "baseline_metrics": baseline,
        "elapsed_seconds": elapsed,
    }

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"\nSaved: {args.output}")

    return results


if __name__ == "__main__":
    main()
