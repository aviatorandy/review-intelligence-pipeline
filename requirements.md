# Requirements

## Functional

R1  Output must be valid JSON matching evals/schema.json.

R2  Every strength and complaint must include >= 1 evidence item where:
    - review_id exists in the input batch
    - quote is an exact verbatim substring of that review's text

R3  Summary bullets with no supporting evidence are allowed but must have confidence="low".
    Strength/complaint items with no evidence are dropped automatically before validation.

R4  Confidence must reflect review count:
    - high   = >= 10 reviews mention the theme (after aggregation across chunks)
    - medium = >= 5 reviews
    - low    = < 5 reviews

R5  Do not invent product features, metrics, or quotes.
    If evidence is missing or unclear, add to "unknowns" instead of claiming.

R6  Executive summary bullets must follow format:
    "[Observation] — [implication or action]"
    Vague observations with no implication are not acceptable.

R7  Sentiment must be computed from CSV label fields (1=positive, 0=negative).
    The model's sentiment estimate is never used.

R8  Duplicate themes must be merged. The top 5 strengths and top 5 complaints
    must represent distinct concepts — not variations of the same theme.

## Non-Functional

R9  Pipeline must support datasets up to 20,000 reviews via chunked processing.

R10 Interrupted runs must be resumable without reprocessing completed chunks.

R11 Input CSV may contain reviews from multiple products.
    Product filtering must be applied before analysis via split_by_product.py.

R12 All processing runs locally — no review data sent to external APIs.
