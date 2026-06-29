"""
Enrich a raw reviews CSV with metadata for faster, higher-quality report generation.

Output columns added:
  topic           - primary topic (ads, crashes, addictiveness, kids, difficulty,
                    download_issues, offline, free_price, gameplay, other)
  sentiment_text  - positive / negative / mixed  (from TEXT, not label)
  severity        - high / medium / low  (for negative signal)
  actionability   - high / medium / low  (can the dev team fix this?)
  is_on_topic     - true/false  (false = review is about a DIFFERENT app)
  short_summary   - 1-sentence plain English summary
  label_conflict  - true if label and text sentiment disagree (mislabeled)

Usage:
  python -m scripts.enrich_reviews --input data/sample/angry_birds_50.csv
  python -m scripts.enrich_reviews --input path/to/reviews.csv --output path/to/enriched.csv
"""
import argparse
import csv
import re
import sys
from pathlib import Path

# ── Topic keyword patterns ─────────────────────────────────────────────────────

TOPICS = {
    "ads": re.compile(
        r"\b(ads?|advert|advertisement|ad.supported|full.screen.ad|pop.?up|banner)\b", re.I
    ),
    "crashes": re.compile(
        r"\b(crash(es|ing|ed)?|force.clos|freeze|frozen|bug(gy)?|corrupt|broke|broken|"
        r"doesn.t.work|won.t.open|stopped.working|glitch)\b", re.I
    ),
    "download_issues": re.compile(
        r"\b(download|install|loading|won.t.load|not.loading|stuck|percent)\b", re.I
    ),
    "addictiveness": re.compile(
        r"\b(addict(ive|ing|ed)?|hooked|can.t.stop|keep.playing|obsess|"
        r"can.t.put.down|hard.to.put.down)\b", re.I
    ),
    "kids_family": re.compile(
        r"\b(kids?|child(ren)?|son|daughter|grandk?ids?|grandson|granddaughter|"
        r"toddler|family|age|year.old|little.one)\b", re.I
    ),
    "difficulty": re.compile(
        r"\b(hard|difficult|challenging|too.easy|impossible|level|stuck|"
        r"walk.?through|beat|pass)\b", re.I
    ),
    "offline": re.compile(
        r"\b(offline|without.internet|no.wifi|no.internet|without.wifi|"
        r"internet.required|connectivity)\b", re.I
    ),
    "free_price": re.compile(
        r"\b(free|price|cost|paid|pay|pennies|worth|money|purchase|buy)\b", re.I
    ),
    "graphics": re.compile(
        r"\b(graphic|visual|screen|display|clear|smooth|render)\b", re.I
    ),
    "gameplay": re.compile(
        r"\b(gameplay|mechanic|level|slingshot|pig|bird|physics|stage|"
        r"launch|shoot|aim|score|star)\b", re.I
    ),
}

# Strong negative language
NEGATIVE_SIGNALS = re.compile(
    r"\b(bad|terrible|awful|hate|hated|worst|broken|crash|bug|useless|"
    r"disappoint|annoy|frustrat|problem|issue|doesn.t.work|slow|lag|"
    r"freez|ruin|horrible|waste|scam|fake|uninstall|remove|not.worth|"
    r"never.again|poor|boring|dumb|stupid|sucks?|stinks?|deleted?|"
    r"not.good|don.t.like|didn.t.like|won.t|cannot)\b",
    re.I,
)

# Strong positive language
POSITIVE_SIGNALS = re.compile(
    r"\b(love|great|amazing|awesome|excellent|fantastic|wonderful|best|"
    r"fun|enjoy|recommend|addictive|addict|favorite|perfect|good|cool|"
    r"brilliant|superb|incredible|outstanding)\b",
    re.I,
)

# Patterns that suggest the review is about a DIFFERENT app mentioning Angry Birds for comparison
OFF_TOPIC_PATTERNS = re.compile(
    r"\b(better than angry birds|like angry birds|unlike angry birds|"
    r"compared to angry birds|angry birds is better|not angry birds|"
    r"instead of angry birds|try angry birds|get angry birds|"
    r"prefer angry birds|similar to angry birds|reminds me of angry birds|"
    r"coattails of angry birds|rip.?off of|riding the coattails)\b",
    re.I,
)

# Phrases that mean "this review is definitely about Angry Birds itself"
ON_TOPIC_ANCHORS = re.compile(
    r"\b(angry birds (is|was|has|have|are|free|game|app|levels?|characters?|"
    r"rovio|season|space|rio|star.wars|birds|pigs|slingshot)|"
    r"i (love|like|play|downloaded?|got|have) angry birds|"
    r"angry birds (free|original|classic|download|update))\b",
    re.I,
)


def classify_topic(text: str) -> str:
    """Return the most prominent topic or 'other'."""
    matches = {topic: bool(pat.search(text)) for topic, pat in TOPICS.items()}
    # Priority order — most actionable topics first
    for topic in ["crashes", "ads", "download_issues", "offline", "addictiveness",
                  "kids_family", "difficulty", "free_price", "gameplay", "graphics"]:
        if matches[topic]:
            return topic
    return "other"


def classify_sentiment_text(text: str) -> str:
    pos = len(POSITIVE_SIGNALS.findall(text))
    neg = len(NEGATIVE_SIGNALS.findall(text))
    if neg >= 2 or (neg >= 1 and pos == 0):
        return "negative"
    if pos > 0 and neg >= 1:
        return "mixed"
    return "positive"


def classify_severity(text: str, sentiment: str) -> str:
    if sentiment == "positive":
        return "low"
    strong = re.search(
        r"\b(terrible|awful|hate|worst|horrible|never again|waste|scam|deleted?|"
        r"uninstall|completely|absolutely|so (bad|boring|dumb|stupid))\b", text, re.I
    )
    if strong:
        return "high"
    moderate = NEGATIVE_SIGNALS.search(text)
    return "medium" if moderate else "low"


def classify_actionability(topic: str, severity: str) -> str:
    high_action = {"crashes", "download_issues", "ads", "offline"}
    low_action = {"addictiveness", "gameplay", "other"}
    if topic in high_action:
        return "high"
    if topic in low_action:
        return "low"
    return "medium"


def is_on_topic(text: str) -> bool:
    """False if the review is clearly about a different app that mentions Angry Birds."""
    if OFF_TOPIC_PATTERNS.search(text):
        # Double-check: if it also has strong on-topic anchors, keep it
        return bool(ON_TOPIC_ANCHORS.search(text))
    return True


def short_summary(text: str, sentiment: str, topic: str) -> str:
    """Rule-based 1-sentence summary."""
    text = text.strip()
    # Truncate very long reviews
    snippet = text[:120].rstrip() + ("..." if len(text) > 120 else "")

    topic_labels = {
        "ads": "about ads",
        "crashes": "about crashes/bugs",
        "download_issues": "about download/install issues",
        "addictiveness": "highlighting addictiveness",
        "kids_family": "about family/kids use",
        "difficulty": "about difficulty/challenge",
        "offline": "about offline play",
        "free_price": "about price/value",
        "gameplay": "about gameplay",
        "graphics": "about graphics",
        "other": "",
    }
    topic_str = topic_labels.get(topic, "")
    prefix = {
        "positive": f"Positive review {topic_str}",
        "negative": f"Negative review {topic_str}",
        "mixed":    f"Mixed review {topic_str}",
    }.get(sentiment, "Review")

    return f"{prefix.strip()}: \"{snippet}\""


def enrich(input_path: str, output_path: str, product_name: str = ""):
    rows_in = []
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_in.append(row)

    fieldnames = list(rows_in[0].keys()) + [
        "topic", "sentiment_text", "severity", "actionability",
        "is_on_topic", "short_summary", "label_conflict",
    ]

    total = len(rows_in)
    on_topic_count = 0
    topic_counts: dict[str, int] = {}

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(rows_in):
            text = row.get("Text", row.get("text", "")).strip()
            label = int(row.get("label", 1))

            sentiment = classify_sentiment_text(text)
            topic = classify_topic(text)
            severity = classify_severity(text, sentiment)
            actionability = classify_actionability(topic, severity)
            on_topic = is_on_topic(text)
            summary = short_summary(text, sentiment, topic)

            # Flag label conflicts (mislabeled reviews)
            label_positive = label == 1
            text_positive = sentiment == "positive"
            conflict = label_positive != text_positive and sentiment != "mixed"

            if on_topic:
                on_topic_count += 1
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

            writer.writerow({
                **row,
                "topic": topic,
                "sentiment_text": sentiment,
                "severity": severity,
                "actionability": actionability,
                "is_on_topic": str(on_topic).lower(),
                "short_summary": summary,
                "label_conflict": str(conflict).lower(),
            })

            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{total} processed...", flush=True)

    # Summary stats
    conflicts = sum(
        1 for r in rows_in
        if classify_sentiment_text(r.get("Text", r.get("text", ""))) != (
            "positive" if int(r.get("label", 1)) == 1 else "negative"
        ) and classify_sentiment_text(r.get("Text", r.get("text", ""))) != "mixed"
    )
    off_topic = total - on_topic_count

    print(f"\n✅ Enriched {total} reviews → {output_path}")
    print(f"   On-topic:      {on_topic_count} / {total}")
    print(f"   Off-topic:     {off_topic} (reviews about other apps)")
    print(f"   Label conflicts: {conflicts} (mislabeled reviews)")
    print(f"\n   Topic breakdown:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"     {topic:<20} {count}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--product", default="", help="Product name for context")
    args = parser.parse_args()

    output = args.output or args.input.replace(".csv", "_enriched.csv")
    enrich(args.input, output, args.product)


if __name__ == "__main__":
    main()
