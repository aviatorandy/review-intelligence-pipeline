"""
Post-aggregation synthesis: generates executive summary and improvement
recommendations from aggregated themes. Marketing quotes are pulled
directly from top_strengths evidence (real quotes, no hallucination).
Listing recommendations removed — too prone to generic/hallucinated output.
"""
import json
from .llm_client import call_llm

SYNTH_SYSTEM = """You are a senior product analyst summarizing customer review data.
You will receive aggregated themes and evidence extracted from real customer reviews.
Output only valid JSON. No markdown, no extra text."""

SYNTH_PROMPT = """Based on the following aggregated review insights, generate a synthesis report.

AGGREGATED DATA:
{data}

Return this exact JSON structure:
{{
  "executive_summary": "2-3 sentence plain-English summary of the overall sentiment and the single most important finding. Write for a product manager or business owner. Be specific to the actual themes in the data.",
  "improvement_recommendations": [
    {{
      "title": "Short action-oriented title",
      "description": "What to fix and why it matters. 1-2 sentences. Must be grounded in a specific theme from the data above.",
      "priority": "high",
      "business_impact": "Concrete effect on ratings, retention, or revenue if this is addressed.",
      "supporting_theme": "Exact theme name from top_complaints or top_strengths this is based on"
    }}
  ]
}}

Rules:
- improvement_recommendations: 3-5 items, ranked by priority (high/medium/low)
- Every recommendation MUST reference a real theme name from the data above — do not invent issues
- executive_summary must mention specific themes, not generic statements
- Write for a non-technical audience"""


def _extract_marketing_quotes(aggregated: dict) -> list:
    """Pull real verbatim quotes from top_strengths evidence. No LLM involved."""
    quotes = []
    seen = set()
    for strength in aggregated.get("top_strengths", []):
        theme = strength.get("theme", "")
        for ev in strength.get("evidence", []):
            q = ev.get("quote", "").strip()
            if q and q not in seen and len(q) > 20:
                quotes.append({"quote": q, "theme": theme})
                seen.add(q)
            if len(quotes) >= 3:
                return quotes
    return quotes


def run_synthesis(aggregated: dict) -> dict:
    """
    Takes aggregated pipeline output and returns enriched synthesis fields.
    Falls back gracefully if LLM call fails.
    """
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
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(raw)
        return {
            "executive_summary": result.get("executive_summary", ""),
            "improvement_recommendations": result.get("improvement_recommendations", []),
            "listing_recommendations": [],
            "top_marketing_quotes": _extract_marketing_quotes(aggregated),
        }
    except Exception as e:
        return {
            "executive_summary": "",
            "improvement_recommendations": [],
            "listing_recommendations": [],
            "top_marketing_quotes": _extract_marketing_quotes(aggregated),
            "_synthesis_error": str(e),
        }


def compute_quality_metrics(chunk_results: list, final: dict) -> dict:
    """Quality checks and hallucination audit aggregated across all chunks."""
    total_chunks = len(chunk_results)
    valid_chunks = sum(1 for r in chunk_results if r is not None)

    all_themes = final.get("top_strengths", []) + final.get("top_complaints", [])
    themes_with_evidence = sum(1 for t in all_themes if t.get("evidence"))
    evidence_coverage = round(themes_with_evidence / len(all_themes), 2) if all_themes else 1.0

    # Aggregate hallucination audit across chunks
    total_evidence = 0
    unverified_quotes = 0
    label_mismatches = 0
    inflated_counts = 0
    chunks_with_flags = 0

    for r in chunk_results:
        if r is None:
            continue
        audit = r.get("_audit", {})
        total_evidence += audit.get("total_evidence", 0)
        unverified_quotes += audit.get("unverified_quotes", 0)
        label_mismatches += audit.get("label_mismatches", 0)
        inflated_counts += audit.get("inflated_counts", 0)
        if audit.get("hallucination_flags", 0) > 0:
            chunks_with_flags += 1

    hallucination_rate = round(unverified_quotes / total_evidence, 3) if total_evidence > 0 else 0.0

    return {
        "schema_pass_rate": round(valid_chunks / total_chunks, 2) if total_chunks else 1.0,
        "evidence_coverage": evidence_coverage,
        "chunks_succeeded": valid_chunks,
        "chunks_total": total_chunks,
        "hallucination": {
            "rate": hallucination_rate,
            "unverified_quotes": unverified_quotes,
            "label_mismatches": label_mismatches,
            "inflated_counts": inflated_counts,
            "chunks_with_flags": chunks_with_flags,
            "total_evidence_checked": total_evidence,
        },
    }
