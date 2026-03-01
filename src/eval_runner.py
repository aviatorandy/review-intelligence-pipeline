import argparse
import json
import os
from datetime import datetime

from .ingest import load_reviews
from .summarize import run_summary
from .validators import validate_json_schema, check_evidence
from .report_printer import print_report
from .report_html import generate_html


def compute_sentiment(rows):
    n = len(rows)
    pos = sum(1 for r in rows if int(r["label"]) == 1)
    neg = n - pos
    return {
        "positive_rate": round(pos / n, 4),
        "negative_rate": round(neg / n, 4),
        "n_reviews": n
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to reviews CSV")
    parser.add_argument("--n", type=int, default=50, help="Number of reviews to sample")
    args = parser.parse_args()

    print(f"Loading reviews from {args.data}...")
    df = load_reviews(args.data)
    sample = df.sample(n=min(args.n, len(df)), random_state=42)
    rows = sample.to_dict(orient="records")
    review_lookup = {r["review_id"]: r["text"] for r in rows}

    print(f"Sampled {len(rows)} reviews. Running summarizer...")
    output_str = run_summary(rows)

    print("Validating output...")
    valid, obj, err = validate_json_schema(output_str, "evals/schema.json")
    if not valid:
        print("❌ JSON validation failed:", err)
        print("\nRaw output from model:\n", output_str[:2000])
        return

    # Override sentiment with ground truth — never trust the model to count
    obj["sentiment"] = compute_sentiment(rows)

    evidence_ok = check_evidence(obj, review_lookup)

    print("JSON valid:", valid)
    print("Evidence valid:", evidence_ok)

    # Save results
    run_dir = f"results/runs/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(run_dir, exist_ok=True)

    with open(f"{run_dir}/output.json", "w") as f:
        json.dump(obj, f, indent=2)

    with open(f"{run_dir}/score.json", "w") as f:
        json.dump({
            "json_valid": valid,
            "evidence_valid": evidence_ok,
            "sentiment": obj["sentiment"],
        }, f, indent=2)

    # Print to terminal
    print_report(obj)

    # Generate HTML report
    generate_html(obj, f"{run_dir}/report.html", data_path=args.data)
    print(f"Open in browser: open {run_dir}/report.html")


if __name__ == "__main__":
    main()
