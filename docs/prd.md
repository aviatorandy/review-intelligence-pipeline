# PRD — Review Intelligence Summarizer

## Problem
Stakeholders cannot quickly identify key themes across many reviews.

## MVP
Given 50–20,000 reviews per product, output a structured summary with:
- 3–6 executive bullets with observations and actionable implications
- Top 5 strengths + top 5 complaints (themes + evidence + review_count)
- Sentiment distribution computed from ground truth labels
- Unknowns

## Data
- Source: Amazon app store reviews CSV with Text and label columns (1=positive, 0=negative)
- Multi-product dataset split into per-product CSVs via split_by_product.py
- Known products: angry_birds, twitter, bible, youtube, facebook, google,
  solitaire, pandora, tunein_radio, euchre, words_with_friends, dropbox

## Architecture
- **Product splitter**: splits multi-product CSV into per-product files (split_by_product.py)
- **Chunked pipeline**: reviews processed in batches of 50 (configurable)
- **Semantic + fuzzy theme aggregation**: two-pass merging catches both conceptually
  identical themes ("Educational value" / "Educational value for children") and
  near-identical phrasings ("Addictive" / "Addictiveness")
- **Resume support**: interrupted runs resume by passing --run-dir
- **Two output formats**: terminal summary + HTML dark-theme report

## CLI
```bash
# Split multi-product CSV into per-product files
python -m src.split_by_product --data "data/angrybirds amazon reviews.csv"

# Quick sample test (single LLM call, good for prompt iteration)
python -m src.eval_runner --data "data/products/angry_birds.csv" --n 50

# Full pipeline on a product
python -m src.full_pipeline --data "data/products/angry_birds.csv"

# Resume interrupted run
python -m src.full_pipeline --data "data/products/angry_birds.csv" --run-dir results/runs/<timestamp>_full
```

## Success Metrics
- Faithfulness (verbatim quote check) >= 98%
- Relevance (quote matches theme keywords) >= 95%
- 0 critical hallucinations (unsupported claim with high confidence)
- Sentiment = 100% accurate (computed in code from labels)
- Output parses as valid JSON >= 99% of runs
- 0 duplicate themes in top 5 (manual check)

## Known Limitations
- Complaint themes unreliable at <200 reviews — too few negatives per chunk
- Mistral 7B copies prompt placeholder text literally — all examples must be realistic
- Theme deduplication requires manual tuning of SEMANTIC_GROUPS when new duplicate
  patterns emerge
- review_count is model-estimated, not programmatically counted — treat as approximate
- 18,714 reviews in original CSV are unclassified (no product keyword in opening text)
