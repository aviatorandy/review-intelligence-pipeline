Analyze the following product reviews and return a JSON object.

CRITICAL: You must use EXACTLY these field names. No other names are acceptable:
- "summary_bullets" (NOT "executive_summary")
- "top_strengths"
- "top_complaints"
- "sentiment" (NOT "sentiment_distribution")
- "unknowns"

Return EXACTLY this structure:

{
  "summary_bullets": [
    {
      "claim": "Addictiveness is the dominant strength — lean into this in marketing copy.",
      "confidence": "high",
      "evidence": [{"review_id": 5, "quote": "this game is incredibly addicting I can not stop playing"}]
    }
  ],
  "top_strengths": [
    {
      "theme": "Fun and addictive gameplay",
      "review_count": 12,
      "confidence": "high",
      "evidence": [{"review_id": 5, "quote": "this game is incredibly addicting I can not stop playing"}]
    }
  ],
  "top_complaints": [
    {
      "theme": "Intrusive ads",
      "review_count": 4,
      "confidence": "medium",
      "evidence": [{"review_id": 15, "quote": "the ads are so long they ruin the experience"}]
    }
  ],
  "sentiment": {
    "positive_rate": 0.76,
    "negative_rate": 0.24,
    "n_reviews": 50
  },
  "unknowns": ["list claims you could not find evidence for"]
}

Rules:

1) summary_bullets: write 3-6 bullets. Each claim must follow this format:
   "[Observation] — [implication or action]"
   Example: "Ads are the #1 complaint — users switch to paid version, signaling a premium upgrade opportunity."
   NOT vague: "Game is fun."

2) top_strengths: up to 5, ranked by review_count descending.
   Merge themes that mean the same thing into ONE entry with a higher count.
   Do NOT list "Wide appeal" AND "Universal appeal" AND "Widespread appeal" separately — pick one name.
   Draw evidence primarily from reviews marked sentiment="POSITIVE".

3) top_complaints: up to 5, ranked by review_count descending.
   IMPORTANT: Each review has a "sentiment" field — either "POSITIVE" or "NEGATIVE".
   - PRIORITIZE evidence from reviews marked sentiment="NEGATIVE" for complaints.
   - Only use sentiment="POSITIVE" reviews as complaint evidence if the complaint is
     explicit and unambiguous (e.g. "I love the game but the ads are terrible").
   - NEVER file a complaint where the evidence quote expresses overall satisfaction.
   - Look hard for complaints — check ALL sentiment="NEGATIVE" reviews first.
   - Common complaint themes: ads, crashes, too difficult, repetitive, boring, high cost,
     limited features, offline issues.
   - If you find ANY negative signal — include it with low confidence rather than leaving
     top_complaints empty.

4) sentiment: count label=1 as positive, label=0 as negative. Count exactly.

5) Every "quote" must be copied CHARACTER FOR CHARACTER from the review text.
   The quote must support the theme — do not cite an unrelated review.

Reviews (JSONL):
{{REVIEWS_JSONL}}
