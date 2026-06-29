"""
Post-aggregation synthesis: generates executive summary, improvement recommendations,
and listing recommendations from the aggregated themes in one LLM call.
"""
import json
from .llm_client import call_llm

SYNTH_SYSTEM = """You are a senior product strategist analyzing Amazon customer reviews.
You will receive aggregated insight data extracted from customer reviews.
Your job is to synthesize this into actionable business recommendations.
Output only valid JSON. No markdown, no extra text."""

SYNTH_PROMPT = """Based on the following aggregated review insights, generate a synthesis report.

AGGREGATED DATA:
{data}

Return this exact JSON structure:
{{
  "executive_summary": "2-3 sentence plain-English summary of overall customer sentiment and the single most important finding. Write for a business owner or product manager.",
  "improvement_recommendations": [
    {{
      "title": "Short action-oriented title",
      "description": "What to fix and why it matters to the business. 1-2 sentences.",
      "priority": "high",
      "business_impact": "What improving this would do for ratings, retention, or revenue.",
      "supporting_theme": "The complaint or pattern this is based on"
    }}
  ],
  "listing_recommendations": [
    {{
      "title": "Short title",
      "description": "Specific change to make to the Amazon listing, title, bullets, or images.",
      "rationale": "Why this change would convert better or reduce negative reviews."
    }}
  ],
  "top_marketing_quotes": [
    {{
      "quote": "Exact customer quote that would work in marketing",
      "review_id": 0,
      "theme": "What strength this illustrates"
    }}
  ]
}}

Rules:
- improvement_recommendations: 3-5 items, ranked by priority (high/medium/low)
- listing_recommendations: 2-4 items
- top_marketing_quotes: 2-3 of the best quotes from top_strengths evidence
- Write for a non-technical audience. No jargon.
- Every recommendation must connect back to specific themes in the data."""


def run_synthesis(aggregated: dict) -> dict:
    """
    Takes aggregated pipeline output and returns enriched synthesis fields.
    Falls back gracefully if LLM call fails.
    """
    # Prepare a condensed version of the data for the prompt
    condensed = {
        "top_strengths": [
            {
                "theme": s["theme"],
                "review_count": s["review_count"],
                "confidence": s["confidence"],
                "sample_quote": s["evidence"][0]["quote"] if s.get("evidence") else "",
            }
            for s in aggregated.get("top_strengths", [])
        ],
        "top_complaints": [
            {
                "theme": c["theme"],
                "review_count": c["review_count"],
                "confidence": c["confidence"],
                "sample_quote": c["evidence"][0]["quote"] if c.get("evidence") else "",
            }
            for c in aggregated.get("top_complaints", [])
        ],
        "summary_bullets": [b["claim"] for b in aggregated.get("summary_bullets", [])],
        "sentiment": aggregated.get("sentiment", {}),
    }

    prompt = SYNTH_PROMPT.format(data=json.dumps(condensed, indent=2))

    try:
        raw = call_llm(SYNTH_SYSTEM, prompt)
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(raw)
        return {
            "executive_summary": result.get("executive_summary", ""),
            "improvement_recommendations": result.get("improvement_recommendations", []),
            "listing_recommendations": result.get("listing_recommendations", []),
            "top_marketing_quotes": result.get("top_marketing_quotes", []),
        }
    except Exception as e:
        # Graceful fallback — report still works without synthesis
        return {
            "executive_summary": "",
            "improvement_recommendations": [],
            "listing_recommendations": [],
            "top_marketing_quotes": [],
            "_synthesis_error": str(e),
        }


def compute_quality_metrics(chunk_results: list, final: dict) -> dict:
    """Lightweight quality checks on pipeline output."""
    total_chunks = len(chunk_results)
    valid_chunks = sum(1 for r in chunk_results if r is not None)

    all_themes = final.get("top_strengths", []) + final.get("top_complaints", [])
    themes_with_evidence = sum(1 for t in all_themes if t.get("evidence"))
    evidence_coverage = round(themes_with_evidence / len(all_themes), 2) if all_themes else 1.0

    bullets_with_evidence = sum(
        1 for b in final.get("summary_bullets", []) if b.get("evidence")
    )
    total_bullets = len(final.get("summary_bullets", []))

    return {
        "schema_pass_rate": round(valid_chunks / total_chunks, 2) if total_chunks else 1.0,
        "evidence_coverage": evidence_coverage,
        "bullets_with_evidence": bullets_with_evidence,
        "total_bullets": total_bullets,
        "chunks_succeeded": valid_chunks,
        "chunks_total": total_chunks,
    }
