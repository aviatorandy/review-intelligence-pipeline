# Review Intelligence Pipeline

An end-to-end AI pipeline that analyzes thousands of app store reviews and generates stakeholder-ready product intelligence reports. Every claim is backed by a verbatim quote from a real review. Runs fully offline using Mistral via Ollama — no API costs, no data leaving your machine.

![Report Preview](results/sample/report.html)

## What It Does
- Splits multi-product review datasets into per-product CSVs automatically
- Extracts top strengths and complaints ranked by how many reviews mention them
- Writes executive summary bullets in the format: `"[Observation] — [implication or action]"`
- Validates every quote is a verbatim substring of the cited review
- Merges duplicate themes using semantic grouping + fuzzy string matching
- Flags hallucinated evidence (wrong field names, unrelated quotes, positive reviews filed as complaints)
- Outputs a dark-themed interactive HTML report and JSON

## Sample Output
```
ANGRY BIRDS · AMAZON REVIEWS · 235 REVIEWS SAMPLED

Sentiment: 93.2% positive  6.8% negative

Executive Summary
  ✦ Addictiveness is the dominant strength — lean into this in marketing copy.
  ✦ Ads are the #1 complaint — users switch to paid version, signaling a premium upgrade path.
  ✦ Wide appeal across all ages — market to families and casual gamers.

Top Strengths                    Top Complaints
  Fun and addictive  90 reviews    Intrusive ads     5 reviews
  Universal appeal   46 reviews    Boredom           2 reviews
  Educational value   6 reviews    High cost         2 reviews
```

## Prerequisites

**1. Install Ollama**
```bash
# macOS
brew install ollama

# or download from https://ollama.com
```

**2. Pull Mistral and start the server**
```bash
ollama pull mistral
ollama serve        # keep this running in a separate terminal
```

**3. Clone the repo and install dependencies**
```bash
git clone https://github.com/yourusername/review-intelligence-pipeline.git
cd review-intelligence-pipeline
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Quickstart

**Try it immediately with the sample data:**
```bash
python -m src.eval_runner --data "data/sample/angry_birds_50.csv" --n 50
open results/runs/$(ls results/runs/ | tail -1)/report.html
```

**Run on your own data:**
```bash
# Step 1 — split a multi-product CSV into per-product files
python -m src.split_by_product --data "data/your_reviews.csv"

# Step 2 — run the full pipeline on a product
python -m src.full_pipeline --data "data/products/angry_birds.csv"

# Step 3 — open the report
open results/runs/$(ls results/runs/ | tail -1)/report.html
```

**Other useful commands:**
```bash
# Limit to a random sample of N reviews
python -m src.full_pipeline --data "data/products/angry_birds.csv" --max-reviews 500

# Change chunk size (default 50, increase for speed, decrease for reliability)
python -m src.full_pipeline --data "data/products/angry_birds.csv" --chunk-size 100

# Resume an interrupted run
python -m src.full_pipeline --data "data/products/angry_birds.csv" --run-dir results/runs/<timestamp>_full
```

## Project Structure
```
src/
  split_by_product.py   detects and splits multi-product CSV into per-product files
  full_pipeline.py      chunked pipeline for large dataset runs with resume support
  eval_runner.py        quick single-call test for prompt iteration
  ingest.py             loads and cleans CSV, assigns review_ids
  summarize.py          builds prompt, adds POSITIVE/NEGATIVE labels, calls LLM
  llm_client.py         Ollama API client (localhost:11434, mistral:latest)
  validators.py         schema + verbatim + relevance checks on all evidence
  report_html.py        generates dark-themed HTML report (product name from filename)
  report_printer.py     terminal summary output

prompts/
  system.md             system prompt — hard faithfulness and no-hallucination rules
  summarize_v1.md       task prompt with explicit JSON structure example

evals/
  schema.json           jsonschema for output validation
  eval_cases.jsonl      reproducible test cases with seeds
  rubric.md             scoring rubric for manual eval

docs/
  prd.md                product requirements and architecture
  eval_strategy.md      metrics, thresholds, and what to watch for
  guardrails.md         hallucination definitions and known failure modes

data/
  sample/
    angry_birds_50.csv  50 reviews for quick testing without full dataset

results/
  sample/
    output.json         sample aggregated output
    report.html         sample HTML report (open in browser)
```

## How It Works

```
Raw CSV (multi-product reviews)
        ↓
split_by_product.py
  → keyword detection in first 150 chars of each review
  → saves per-product CSVs to data/products/
        ↓
full_pipeline.py
  → random sample (reproducible with seed=42)
  → splits into chunks of 50 reviews
  → appends dedicated negative-only chunk to surface complaints
        ↓
For each chunk:
  summarize.py   → builds prompt with POSITIVE/NEGATIVE labels
  llm_client.py  → sends to Mistral via Ollama
  validators.py  → checks schema, verbatim quotes, theme relevance
                 → strips positive-labeled reviews from complaints
  saved to chunks/chunk_NNNN.json
        ↓
aggregate_chunks()
  → semantic group matching  (catches "Wide appeal" vs "Universal appeal")
  → fuzzy string matching    (catches "Addictive" vs "Addictiveness")  
  → sums review_counts
  → recomputes confidence from actual counts (not trusted from model)
        ↓
report_html.py  → report.html  (product name derived from filename)
report_printer.py → terminal summary
```

## Validation System

| Check | What It Catches | Where |
|-------|----------------|-------|
| Schema validity | Wrong field names, missing required fields | validators.py |
| Verbatim check | Paraphrased or invented quotes | validators.py |
| Relevance check | Quotes that don't match their theme | validators.py |
| Sentiment filter | Positive reviews filed as complaints | full_pipeline.py |
| Confidence recompute | Model-inflated confidence scores | full_pipeline.py |

## Key Design Decisions
- **Sentiment from labels, never the model** — ground truth CSV labels always override model estimates
- **Dedicated negative chunk** — all negative reviews run together as one focused chunk, guaranteeing complaint signal even at 3-4% negative rate
- **Two-pass theme deduplication** — semantic groups catch conceptually identical themes; fuzzy matching catches near-identical phrasings
- **Explicit POSITIVE/NEGATIVE labels in prompt** — tells Mistral which reviews to prioritize for complaints vs strengths
- **review_count is model-estimated** — summed across chunks, treat as approximate ranking signal not exact count

## Known Products in Sample Dataset
`angry_birds` · `twitter` · `bible` · `youtube` · `facebook` · `google` · `solitaire` · `pandora` · `tunein_radio` · `euchre` · `words_with_friends` · `dropbox`

## Tech Stack
Python · Mistral 7B · Ollama · rapidfuzz · jsonschema · pandas

## License
MIT
