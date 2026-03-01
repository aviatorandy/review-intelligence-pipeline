# Eval Strategy

## Metrics

### 1) JSON Validity
- % outputs that parse and match schema
- Checked automatically in validators.py via jsonschema
- Markdown code fences stripped before parsing (Mistral sometimes adds them)
- Empty evidence arrays on summary_bullets are now allowed (schema relaxed)
- Strength/complaint items with empty evidence are silently dropped before validation

### 2) Faithfulness
- % claims where evidence quote is a verbatim substring of the cited review text
- Checked in check_evidence() in validators.py
- Applies to: summary_bullets, top_strengths, top_complaints

### 3) Relevance
- % evidence items where the quote semantically matches the theme label
- Checked via keyword mapping in check_relevance() in validators.py
- Catches hallucinated theme labels (e.g. "Ads" theme backed by an unrelated quote)
- 16 known theme categories: ads, crash, fun, addictive, boring, free, difficulty,
  difficulty for children, offline, levels, kids/educational, compatibility, graphics,
  update, price, popular
- Unknown themes pass through unverified — expand THEME_KEYWORDS as new themes emerge

### 4) Sentiment Accuracy
- positive_rate / negative_rate computed directly from CSV labels in code
- Model sentiment output is never trusted — always overridden with ground truth
- Always 100% accurate by design

### 5) Theme Deduplication Quality
- Themes are merged using two strategies in order:
  1. Semantic group matching — themes sharing a concept keyword merge automatically
     (e.g. "Educational value" + "Educational value for children" → one theme)
  2. Fuzzy string matching — near-identical phrasings merge via rapidfuzz (threshold: 70)
- If duplicates appear in the report, add the shared concept word to SEMANTIC_GROUPS
  in full_pipeline.py — that is the tuning knob

### 6) Theme Quality (manual on small set)
- Overlap between model themes and human-tagged themes for 10–20 cases
- Run multiple times with different seeds — themes should be consistent across runs
- Executive bullets should follow format: "[Observation] — [implication or action]"

## Pass Thresholds
- JSON validity >= 99%
- Faithfulness >= 98%
- Relevance >= 95%
- Sentiment accuracy = 100% (enforced in code)
- Duplicate themes in top 5 = 0 (manual check)

## How to Run Evals
```bash
# Single sample eval (fast, good for prompt iteration)
python -m src.eval_runner --data "data/products/angry_birds.csv" --n 50

# Full pipeline — recommended minimum for reliable complaint themes
python -m src.full_pipeline --data "data/products/angry_birds.csv"

# Other product files
python -m src.full_pipeline --data "data/products/twitter.csv"
python -m src.full_pipeline --data "data/products/bible.csv"
```

## What to Watch For
- Empty report → check results/runs/<timestamp>/chunks/chunk_0000_error.txt
- "exact substring from that review" appearing as a quote → Mistral copied the prompt
  example — check prompts/summarize_v1.md example values are realistic not placeholder text
- Duplicate themes in strengths → add shared keyword to SEMANTIC_GROUPS in full_pipeline.py
- Complaints section empty → sparse negatives, increase sample size or check prompt
- Irrelevant evidence → model hallucinating theme labels, increase sample or tighten prompt
