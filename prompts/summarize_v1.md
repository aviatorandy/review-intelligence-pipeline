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
   Draw evidence primarily from reviews where the TEXT expresses clear satisfaction or praise.

3) top_complaints: up to 5, ranked by review_count descending.

   GROUND TRUTH RULE — READ THIS CAREFULLY:
   The `sentiment` field in each review is derived from a dataset label and may be WRONG.
   Always treat the TEXT of the review as the source of truth.

   A complaint is only valid if:
   a) The review text EXPLICITLY describes a problem, frustration, or negative experience
   b) The evidence quote DIRECTLY expresses dissatisfaction — words like "hate", "crash",
      "broken", "annoying", "doesn't work", "too many ads", "disappointing", etc.
   c) You can read the quote cold and immediately understand what the user dislikes.

   STRICTLY FORBIDDEN — these DISQUALIFY a complaint:
   - A quote that is purely complimentary or enthusiastic (e.g. "THIS IS A VERY GOOD APP")
   - A quote that praises the product with no complaint buried in it
   - Manufacturing a complaint theme that isn't explicitly stated in any review text
   - Using a review as evidence just because its sentiment label says "NEGATIVE"

   SELF-CHECK: Before including any complaint, re-read the evidence quote. Ask yourself:
   "Does this quote actually express frustration or identify a problem?" 
   If the answer is no, DO NOT include it.

   It is CORRECT and EXPECTED to return fewer than 5 complaints, or even an empty
   top_complaints list, if the reviews in this batch don't contain genuine complaints.
   An empty list is far better than fabricated complaints.

4) sentiment: count label=1 as positive, label=0 as negative. Count exactly.

5) Every "quote" must be copied CHARACTER FOR CHARACTER from the review text.
   The quote must directly support the theme — not be loosely associated with it.

Reviews (JSONL):
{{REVIEWS_JSONL}}
