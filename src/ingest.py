import pandas as pd


# Column names that identify a per-app/product grouping field
_APP_COLUMN_CANDIDATES = {"app", "product", "product_name", "app_name", "category", "title"}


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
    df = df.rename(columns=col_map)

    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0].copy()
    df["review_id"] = range(len(df))

    keep = ["review_id", "text", "label"]
    if "app" in df.columns:
        df["app"] = df["app"].astype(str).str.strip()
        keep.append("app")

    return df[keep]


def detect_apps(df: pd.DataFrame) -> list[str] | None:
    """Return sorted list of app names if an 'app' column is present, else None."""
    if "app" not in df.columns:
        return None
    apps = sorted(df["app"].dropna().unique().tolist())
    return apps if len(apps) > 1 else None