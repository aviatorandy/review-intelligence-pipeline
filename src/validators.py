import json
from jsonschema import validate
from jsonschema.exceptions import ValidationError


def validate_json_schema(output_str: str, schema_path: str):
    # Strip markdown code fences if the model added them
    cleaned = output_str.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        obj = json.loads(cleaned)

        # Strip empty evidence arrays from summary_bullets before validation
        # Mistral sometimes leaves evidence: [] on low-confidence bullets
        for bullet in obj.get("summary_bullets", []):
            if not bullet.get("evidence"):
                bullet["evidence"] = []  # already empty, schema now allows it

        # Remove any strength/complaint items with empty evidence entirely
        obj["top_strengths"] = [s for s in obj.get("top_strengths", []) if s.get("evidence")]
        obj["top_complaints"] = [c for c in obj.get("top_complaints", []) if c.get("evidence")]

        schema = json.load(open(schema_path))
        validate(instance=obj, schema=schema)
        return True, obj, None
    except json.JSONDecodeError as e:
        return False, None, f"JSON parse error: {e}"
    except ValidationError as e:
        return False, None, f"Schema error: {e.message}"


def check_evidence(obj, review_lookup):
    """
    Check 1 — Verbatim: quote must exist exactly in the cited review text.
    Check 2 — Relevance: quote must be semantically related to the theme/claim.
    """
    failures = []

    for section in ["summary_bullets", "top_strengths", "top_complaints"]:
        for item in obj.get(section, []):
            label = item.get("theme") or item.get("claim") or ""

            for ev in item.get("evidence", []):
                rid = ev["review_id"]
                quote = ev["quote"]

                # Check 1: verbatim quote exists in review
                if rid not in review_lookup:
                    failures.append({
                        "type": "missing_review",
                        "section": section,
                        "theme": label,
                        "review_id": rid,
                        "quote": quote[:80]
                    })
                elif quote not in review_lookup[rid]:
                    failures.append({
                        "type": "quote_not_verbatim",
                        "section": section,
                        "theme": label,
                        "review_id": rid,
                        "quote": quote[:80]
                    })
                else:
                    # Check 2: relevance
                    relevance_issue = check_relevance(label, quote)
                    if relevance_issue:
                        failures.append({
                            "type": "irrelevant_evidence",
                            "section": section,
                            "theme": label,
                            "review_id": rid,
                            "quote": quote[:80],
                            "reason": relevance_issue
                        })

    if failures:
        print(f"\n  ⚠️  {len(failures)} evidence issue(s) found:")
        for f in failures[:8]:
            if f["type"] == "irrelevant_evidence":
                print(f"    ❌ [{f['section']}] Theme: \"{f['theme']}\"")
                print(f"       Quote: \"{f['quote']}\"")
                print(f"       Reason: {f['reason']}")
            else:
                print(f"    ❌ [{f['type']}] review_id={f['review_id']} theme=\"{f['theme']}\"")
        return False

    return True


# ─── Relevance checking ───────────────────────────────────────────────────────

THEME_KEYWORDS = {
    "ads":                    ["ad", "ads", "advertisement", "pop-up", "popup", "banner", "sponsor", "commercial", "ad-free", "ad free", "suggestive"],
    "crash":                  ["crash", "crashes", "crashed", "force close", "closes", "freezes", "freeze", "broken", "bug", "corrupt", "corrupted"],
    "fun":                    ["fun", "enjoy", "great", "love", "awesome", "amazing", "best", "fantastic", "wonderful", "entertain"],
    "addictive":              ["addictive", "addicting", "addicted", "can't stop", "hooked", "obsessed", "keep playing", "hard to put down"],
    "boring":                 ["boring", "bored", "dull", "repetitive", "pointless", "waste", "not fun", "don't like", "terrible", "awful"],
    "free":                   ["free", "no cost", "doesn't cost", "without paying", "no charge"],
    "difficulty":             ["hard", "difficult", "frustrating", "impossible", "too easy", "challenging", "walk-through", "walkthrough"],
    "difficulty for children":["too hard for", "child can't", "difficult for kids", "not for children", "too complex for"],
    "offline":                ["offline", "wifi", "internet", "connection", "no wifi", "without wifi", "no internet", "online", "sign in", "requires internet"],
    "levels":                 ["level", "levels", "stage", "stages", "worlds", "episodes"],
    "kids":                   ["kid", "kids", "child", "children", "family", "age", "young", "son", "daughter", "grandchild"],
    "compatibility":          ["kindle", "device", "compatible", "works on", "doesn't work", "install", "kindle fire"],
    "graphics":               ["graphic", "graphics", "visual", "looks", "display", "screen", "animation"],
    "update":                 ["update", "updated", "version", "new version", "latest", "patch"],
    "price":                  ["price", "cost", "paid", "purchase", "buy", "expensive", "cheap", "worth"],
    "popular":                ["popular", "famous", "everyone", "world", "known", "heard about"],
}


def get_theme_category(theme_label: str):
    """Map a theme label to one of our keyword categories."""
    label_lower = theme_label.lower()

    # Direct category name match first
    for category in THEME_KEYWORDS:
        if category in label_lower:
            return category

    # Partial keyword match in the label itself
    for category, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in label_lower:
                return category

    return None


def check_relevance(theme_label: str, quote: str) -> str | None:
    """
    Returns an error string if the quote is clearly irrelevant to the theme.
    Returns None if the quote seems fine or theme is unknown.
    """
    category = get_theme_category(theme_label)
    if category is None:
        return None  # unknown theme — pass through

    keywords = THEME_KEYWORDS[category]
    quote_lower = quote.lower()

    if any(kw in quote_lower for kw in keywords):
        return None  # relevant

    return (
        f"Theme '{theme_label}' expects keywords like {keywords[:3]} "
        f"but none found in quote"
    )
