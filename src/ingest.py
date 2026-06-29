import pandas as pd

# Column names that identify a per-app/product grouping field
_APP_COLUMN_CANDIDATES = {"app", "product", "product_name", "app_name", "category", "title"}

# Enrichment columns produced by scripts/enrich_reviews.py
ENRICHED_COLUMNS = {"topic", "sentiment_text", "severity", "actionability", "label_conflict"}


def load_reviews(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Normalise required columns
    col_map = {}
    for col in df.columns:
        lower = col.strip().lower()
        if lower == "text":
            col_map[col] = "text"
        elif lower == "label":
            col_map[col] = "label"
        elif lower in _APP_COLUMN_CANDIDATES:
            col_map[col] = "app"
        elif lower in ENRICHED_COLUMNS:
            col_map[col] = lower
    df = df.rename(columns=col_map)

    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0].copy()

    # If enriched: drop reviews flagged as mislabeled (label=0 but clearly positive text)
    if "label_conflict" in df.columns:
        before = len(df)
        df = df[df["label_conflict"].astype(str).str.lower() != "true"].copy()
        dropped = before - len(df)
        if dropped:
            print(f"[ingest] Dropped {dropped} label-conflict reviews")

    df["review_id"] = range(len(df))

    keep = ["review_id", "text", "label"]
    if "app" in df.columns:
        df["app"] = df["app"].astype(str).str.strip()
        keep.append("app")

    # Carry enrichment columns through if present
    for col in ("topic", "sentiment_text", "severity", "actionability"):
        if col in df.columns:
            keep.append(col)

    return df[keep]


def is_enriched(df: pd.DataFrame) -> bool:
    """True if the CSV has been pre-enriched with topic/sentiment metadata."""
    return "topic" in df.columns and "sentiment_text" in df.columns


def detect_apps(df: pd.DataFrame) -> list[str] | None:
    """Return sorted list of app names if an 'app' column is present, else None."""
    if "app" not in df.columns:
        return None
    apps = sorted(df["app"].dropna().unique().tolist())
    return apps if len(apps) > 1 else None
