# Guardrails

## Hard Rules (enforced in prompts)
- No fabrication: all claims must be supported by a quoted review text substring
- No demographic inference
- Do not overstate sentiment — must be computed from provided labels only
- If uncertain: state uncertainty in "unknowns" field, do not claim it
- Executive bullets must follow format: "[Observation] — [implication or action]"
  Not allowed: vague statements like "Game is fun" with no actionable implication

## Hallucination Definition
Any claim that is not supported by an evidence quote that appears verbatim in the cited review text.

## Automated Checks (validators.py)
1. **Verbatim check** — quote must exist character-for-character in the cited review
2. **Relevance check** — quote must contain keywords consistent with the theme label
   - Catches cases where the model labels a theme but cites an unrelated review
   - Example caught: Theme "Ads" → quote about opossums → flagged
   - Example caught: Theme "Difficulty for children" → positive quote about 5-year-old → flagged

## Prompt Guardrails (summarize_v1.md)
- Example JSON in prompt uses realistic fake quotes, not placeholder text
  (Mistral copies placeholder text literally if given generic examples like "exact substring from that review")
- Complaints rule: only include genuine complaints — do not label a theme as a complaint
  if the evidence quote is positive
- Deduplication rule: merge themes that mean the same thing — do not create
  "Wide appeal" AND "Universal appeal" AND "Widespread appeal" as separate entries

## Known Failure Modes
- **Placeholder copying**: Mistral copies example values from the prompt verbatim.
  Keep all prompt examples realistic and specific.
- **Sparse negatives**: fewer than ~20 negative reviews in a sample leads to hallucinated
  complaint evidence. Mitigation: run full product CSVs, not small max-reviews samples.
- **Theme label drift**: model uses slightly different names across chunks.
  Mitigation: semantic group matching + fuzzy merging in full_pipeline.py.
- **Empty evidence on low-confidence bullets**: Mistral sometimes produces summary bullets
  with no evidence when confidence is low. Mitigation: schema allows empty evidence on
  bullets; items are dropped silently from strengths/complaints.

## What Is Not Checked (manual review needed)
- Whether the theme represents a meaningful insight vs an obvious observation
- Whether review_count estimates are accurate (model-reported, not counted in code)
- Whether summary bullets are representative of the full dataset
- Whether the "implication" in each bullet is actually actionable and correct
