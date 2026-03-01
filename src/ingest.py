import pandas as pd

def load_reviews(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.rename(columns={"Text": "text", "label": "label"})
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0].copy()
    df["review_id"] = range(len(df))
    return df[["review_id", "text", "label"]]