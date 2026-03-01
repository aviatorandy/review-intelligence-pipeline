"""
Pretty-prints a results output.json to the terminal.
Usage: python -m src.report_printer --file results/runs/<timestamp>/output.json
"""
import argparse
import json


def bar(rate, width=30):
    filled = int(rate * width)
    return "█" * filled + "░" * (width - filled)


def print_report(obj):
    sentiment = obj.get("sentiment", {})
    pos = sentiment.get("positive_rate", 0)
    neg = sentiment.get("negative_rate", 0)
    n = sentiment.get("n_reviews", 0)

    print("\n" + "=" * 60)
    print("  REVIEW INTELLIGENCE REPORT")
    print("=" * 60)

    print(f"\n📊 SENTIMENT  ({n} reviews sampled)")
    print(f"  Positive {bar(pos)} {pos*100:.1f}%")
    print(f"  Negative {bar(neg)} {neg*100:.1f}%")

    print("\n📋 EXECUTIVE SUMMARY")
    for i, b in enumerate(obj.get("summary_bullets", []), 1):
        conf = b.get("confidence", "?")
        icon = "🟢" if conf == "high" else "🟡" if conf == "medium" else "🔴"
        print(f"  {i}. {icon} {b['claim']}")

    print("\n✅ TOP STRENGTHS")
    for s in obj.get("top_strengths", []):
        count = s.get("review_count", "?")
        conf = s.get("confidence", "?")
        icon = "🟢" if conf == "high" else "🟡" if conf == "medium" else "🔴"
        print(f"  {icon} [{count} reviews]  {s['theme']}")
        for ev in s.get("evidence", [])[:1]:
            print(f"      └─ \"{ev['quote'][:80]}...\"" if len(ev['quote']) > 80 else f"      └─ \"{ev['quote']}\"")

    print("\n❌ TOP COMPLAINTS")
    for c in obj.get("top_complaints", []):
        count = c.get("review_count", "?")
        conf = c.get("confidence", "?")
        icon = "🟢" if conf == "high" else "🟡" if conf == "medium" else "🔴"
        print(f"  {icon} [{count} reviews]  {c['theme']}")
        for ev in c.get("evidence", [])[:1]:
            print(f"      └─ \"{ev['quote'][:80]}...\"" if len(ev['quote']) > 80 else f"      └─ \"{ev['quote']}\"")

    unknowns = obj.get("unknowns", [])
    if unknowns:
        print("\n❓ UNKNOWNS / INSUFFICIENT EVIDENCE")
        for u in unknowns:
            print(f"  • {u}")

    print("\n" + "=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to output.json")
    args = parser.parse_args()

    with open(args.file) as f:
        obj = json.load(f)

    print_report(obj)


if __name__ == "__main__":
    main()
