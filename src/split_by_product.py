"""
Splits a multi-product reviews CSV into separate per-product CSV files.

Usage:
    python -m src.split_by_product --data "data/angrybirds amazon reviews.csv"

Output:
    data/products/angry_birds.csv
    data/products/twitter.csv
    data/products/bible.csv
    ... etc
"""
import argparse
import os
import pandas as pd
from pathlib import Path


# ─── Product definitions ──────────────────────────────────────────────────────
# Each entry: (output filename, [keywords to match in first 150 chars of review])
# Keywords are checked in order — first match wins.
# A review is assigned to the FIRST product whose keyword appears in the opening text.

PRODUCTS = [
    ("angry_birds",         ["angry birds", "rovio"]),
    ("twitter",             ["twitter"]),
    ("bible",               ["bible", "thy word"]),
    ("youtube",             ["youtube"]),
    ("facebook",            ["facebook"]),
    ("pandora",             ["pandora"]),
    ("solitaire",           ["solitaire"]),
    ("tunein_radio",        ["tunein", "tune in radio"]),
    ("euchre",              ["euchre"]),
    ("words_with_friends",  ["words with friends"]),
    ("dropbox",             ["dropbox"]),
    ("google",              ["google play", "google maps", "google calendar", "google drive"]),
]


def classify_review(text_lower: str) -> str | None:
    """Return the product key if the review matches, else None."""
    snippet = text_lower[:150]
    for product_key, keywords in PRODUCTS:
        if any(kw in snippet for kw in keywords):
            return product_key
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to combined reviews CSV")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: same folder as input + /products)")
    args = parser.parse_args()

    input_path = Path(args.data)
    out_dir = Path(args.out_dir) if args.out_dir else input_path.parent / "products"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)
    df = df.rename(columns={"Text": "text"})
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0].copy()
    df["text_lower"] = df["text"].str.lower()

    total = len(df)
    print(f"Total reviews: {total}\n")

    # Classify each review
    df["product"] = df["text_lower"].apply(classify_review)

    # Save per-product CSVs
    print("Splitting into product files...")
    assigned = 0
    for product_key, _ in PRODUCTS:
        subset = df[df["product"] == product_key][["text", "label"]].copy()
        subset = subset.rename(columns={"text": "Text"})
        if len(subset) == 0:
            continue
        out_path = out_dir / f"{product_key}.csv"
        subset.to_csv(out_path, index=False)
        assigned += len(subset)
        print(f"  ✅ {product_key:25s} {len(subset):>5} reviews  →  {out_path}")

    # Save unclassified reviews separately
    unclassified = df[df["product"].isna()][["text", "label"]].copy()
    unclassified = unclassified.rename(columns={"text": "Text"})
    unclassified_path = out_dir / "unclassified.csv"
    unclassified.to_csv(unclassified_path, index=False)

    print(f"\n  ❓ unclassified           {len(unclassified):>5} reviews  →  {unclassified_path}")
    print(f"\nTotal assigned:   {assigned}/{total}")
    print(f"Unclassified:     {len(unclassified)}/{total}")
    print(f"\nAll files saved to: {out_dir}/")
    print("\nRun analysis on any product:")
    print(f"  python -m src.full_pipeline --data \"{out_dir}/angry_birds.csv\"")
    print(f"  python -m src.full_pipeline --data \"{out_dir}/twitter.csv\"")
    print(f"  python -m src.full_pipeline --data \"{out_dir}/bible.csv\"")


if __name__ == "__main__":
    main()
