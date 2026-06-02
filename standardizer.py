"""
Product Datasheet Standardizer
==============================
Takes 20+ messy product CSV files and produces a single, clean, unified dataset.

Pipeline steps:
1. Load & merge all CSVs, detect schema differences
2. Standardize column names, data types, units
3. Handle missing values (flag vs. impute based on field type)
4. Fuzzy-match duplicate products
5. Output: clean unified CSV + quality report
"""

import os
import re
import glob
import pandas as pd
import numpy as np
from rapidfuzz import fuzz, process
from collections import Counter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 85 balances catching real dupes (e.g. "Kitchen Timer Countdown Reminder" vs
# "Kitchen Timer Countdown Cooking") without false-flagging unrelated products.
# Tested 80 (too many false positives) and 90 (missed obvious dupes).
FUZZY_THRESHOLD = 85

# Columns with >70% nulls add noise — they only exist in a few source files
# and aren't useful for a unified dataset. We log them in the report, then drop.
DROP_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# Step 1: Load & Merge
# ---------------------------------------------------------------------------
def load_all_csvs(data_dir):
    """Load all CSVs from the data directory and return a list of (filename, df) tuples."""
    csv_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    datasets = []
    for f in sorted(csv_files):
        try:
            df = pd.read_csv(f, low_memory=False)
            df["_source_file"] = os.path.basename(f)
            datasets.append((os.path.basename(f), df))
            print(f"  Loaded {os.path.basename(f)}: {len(df)} rows, {len(df.columns)} cols")
        except Exception as e:
            print(f"  SKIP {os.path.basename(f)}: {e}")
    return datasets


def detect_schema_differences(datasets):
    """Compare column sets across files and report differences."""
    all_columns = {}
    for name, df in datasets:
        all_columns[name] = set(df.columns) - {"_source_file"}

    # Find the union of all columns
    union_cols = set()
    for cols in all_columns.values():
        union_cols |= cols

    schema_report = []
    for name, cols in all_columns.items():
        missing = union_cols - cols
        if missing:
            schema_report.append({"file": name, "missing_columns": sorted(missing)})

    return union_cols, schema_report


def merge_datasets(datasets):
    """Concatenate all DataFrames, aligning on the union of columns."""
    dfs = [df for _, df in datasets]
    merged = pd.concat(dfs, ignore_index=True, sort=False)
    return merged


# ---------------------------------------------------------------------------
# Step 2: Standardize Column Names & Types
# ---------------------------------------------------------------------------
COLUMN_NAME_MAP = {}  # populated dynamically


def standardize_column_names(df):
    """Normalize column names: lowercase, underscores, strip whitespace."""
    rename_map = {}
    for col in df.columns:
        cleaned = col.strip().lower()
        cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
        cleaned = cleaned.strip("_")
        rename_map[col] = cleaned

    df = df.rename(columns=rename_map)

    # Merge common synonyms (includes actual SHEIN dataset columns)
    synonym_map = {
        "product_name": ["name", "item_name", "product_title", "title",
                         "goods_title_link"],
        "product_name_full": ["goods_title_link_jump"],
        "product_url": ["goods_title_link_jump_href"],
        "price": ["cost", "retail_price", "sale_price", "current_price"],
        "category": ["cat", "product_category", "main_category", "category_name"],
        "rank": ["rank_title"],
        "rank_detail": ["rank_sub"],
        "description": ["desc", "product_description", "details", "product_details"],
        "rating": ["avg_rating", "average_rating", "star_rating", "stars"],
        "color": ["colour", "product_color", "product_colour"],
        "brand": ["brand_name", "manufacturer"],
        "size": ["product_size", "item_size"],
    }

    reverse_map = {}
    for canonical, aliases in synonym_map.items():
        for alias in aliases:
            reverse_map[alias] = canonical

    final_rename = {}
    for col in df.columns:
        if col in reverse_map:
            final_rename[col] = reverse_map[col]

    df = df.rename(columns=final_rename)

    # If duplicate columns after renaming, keep first
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def standardize_data_types(df):
    """Convert columns to appropriate types and clean formatting."""
    # Coalesce product_name: use short name, fill gaps with full name
    if "product_name" in df.columns and "product_name_full" in df.columns:
        df["product_name"] = df["product_name"].fillna(df["product_name_full"])
        df = df.drop(columns=["product_name_full"])

    # Extract category from source file name (e.g., "us-shein-electronics-4395.csv" -> "Electronics")
    src_col = "_source_file" if "_source_file" in df.columns else "source_file" if "source_file" in df.columns else None
    if src_col:
        df["category"] = (
            df[src_col]
            .str.replace(r"us-shein-", "", regex=True)
            .str.replace(r"-\d+\.csv", "", regex=True)
            .str.replace("_", " ")
            .str.title()
        )

    # Price columns: strip currency symbols, convert to float
    price_cols = [c for c in df.columns if "price" in c]
    for col in price_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"[^\d.]", "", regex=True)
                .replace("", np.nan)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Rating: clamp to 0-5 range
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df.loc[df["rating"] > 5, "rating"] = np.nan
        df.loc[df["rating"] < 0, "rating"] = np.nan

    # Standardize text fields: strip whitespace, title case for names
    text_cols = ["product_name", "category", "color", "brand"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", np.nan)

    return df


# ---------------------------------------------------------------------------
# Step 3: Handle Missing Values
# ---------------------------------------------------------------------------
def handle_missing_values(df):
    """Handle missing values based on field type."""
    missing_report = {}

    for col in df.columns:
        n_missing = df[col].isna().sum()
        if n_missing == 0:
            continue

        pct_missing = n_missing / len(df) * 100
        missing_report[col] = {"count": int(n_missing), "pct": round(pct_missing, 2)}

        # Strategy by column type
        if df[col].dtype in ["float64", "int64"]:
            # Numeric: fill with median if < 30% missing, else flag
            if pct_missing < 30:
                df[col] = df[col].fillna(df[col].median())
                missing_report[col]["action"] = "filled_median"
            else:
                missing_report[col]["action"] = "left_as_nan"
        else:
            # Categorical/text: fill with "Unknown" if < 50% missing
            if pct_missing < 50:
                df[col] = df[col].fillna("Unknown")
                missing_report[col]["action"] = "filled_unknown"
            else:
                missing_report[col]["action"] = "left_as_nan"

    return df, missing_report


# ---------------------------------------------------------------------------
# Step 4: Fuzzy Deduplication
# ---------------------------------------------------------------------------
def find_duplicates(df, name_col="product_name", threshold=FUZZY_THRESHOLD):
    """Find near-duplicate products using fuzzy string matching on product names."""
    if name_col not in df.columns:
        print(f"  Column '{name_col}' not found — skipping dedup")
        return df, []

    # Work on non-null names only
    mask = df[name_col].notna()
    names = df.loc[mask, name_col].astype(str).tolist()

    if len(names) == 0:
        return df, []

    # For large datasets, sample to keep runtime reasonable
    MAX_DEDUP_CHECK = 10000
    if len(names) > MAX_DEDUP_CHECK:
        print(f"  Sampling {MAX_DEDUP_CHECK} of {len(names)} names for dedup check")
        sample_idx = np.random.choice(len(names), MAX_DEDUP_CHECK, replace=False)
        sample_names = [names[i] for i in sample_idx]
    else:
        sample_names = names

    # Find clusters of duplicates
    seen = set()
    duplicate_groups = []

    for i, name in enumerate(sample_names):
        if i in seen:
            continue

        # Find matches above threshold
        matches = process.extract(
            name, sample_names, scorer=fuzz.token_sort_ratio, limit=5
        )
        group = [i]
        for match_name, score, idx in matches:
            if idx != i and score >= threshold and idx not in seen:
                group.append(idx)
                seen.add(idx)

        if len(group) > 1:
            duplicate_groups.append(
                {"names": [sample_names[j] for j in group], "score": matches[1][1] if len(matches) > 1 else 0}
            )
            seen.add(i)

    # Remove duplicates (keep first occurrence)
    rows_before = len(df)
    df = df.drop_duplicates(subset=[name_col], keep="first")
    rows_removed = rows_before - len(df)

    print(f"  Exact duplicates removed: {rows_removed}")
    print(f"  Fuzzy duplicate groups found: {len(duplicate_groups)}")

    return df, duplicate_groups


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def run_pipeline():
    print("=" * 60)
    print("PRODUCT DATASHEET STANDARDIZER")
    print("=" * 60)

    # Step 1: Load
    print("\n[1/5] Loading CSV files...")
    datasets = load_all_csvs(DATA_DIR)
    print(f"  Total files loaded: {len(datasets)}")

    union_cols, schema_report = detect_schema_differences(datasets)
    print(f"  Union of all columns: {len(union_cols)}")
    if schema_report:
        print(f"  Files with missing columns: {len(schema_report)}")

    # Step 2: Merge
    print("\n[2/5] Merging into unified dataset...")
    df = merge_datasets(datasets)
    print(f"  Merged shape: {df.shape}")

    # Step 3: Standardize
    print("\n[3/5] Standardizing columns and data types...")
    df = standardize_column_names(df)
    df = standardize_data_types(df)
    print(f"  Columns after standardization: {list(df.columns)}")

    # Step 4: Drop near-empty columns
    print("\n[4/6] Dropping columns with >70% missing data...")
    dropped_cols = []
    for col in df.columns:
        if col in ("_source_file", "source_file", "category"):
            continue
        pct_null = df[col].isna().mean()
        if pct_null > DROP_THRESHOLD:
            dropped_cols.append((col, round(pct_null * 100, 1)))
    if dropped_cols:
        df = df.drop(columns=[c for c, _ in dropped_cols])
        for col, pct in dropped_cols:
            print(f"  Dropped '{col}' ({pct}% null)")
    print(f"  Columns remaining: {len(df.columns)}")

    # Step 5: Handle remaining missing values
    print("\n[5/6] Handling missing values...")
    df, missing_report = handle_missing_values(df)
    for col, info in list(missing_report.items())[:10]:
        print(f"  {col}: {info['pct']}% missing -> {info['action']}")
    if len(missing_report) > 10:
        print(f"  ... and {len(missing_report) - 10} more columns")

    # Step 6: Deduplication
    print("\n[6/6] Detecting duplicates...")
    # Use product_name if available, otherwise try the first text-like column
    name_col = "product_name"
    if name_col not in df.columns:
        text_cols = [c for c in df.columns if df[c].dtype == "object" and df[c].notna().sum() > len(df) * 0.5]
        if text_cols:
            name_col = text_cols[0]
            print(f"  Using '{name_col}' for dedup (product_name not found)")
    df, dup_groups = find_duplicates(df, name_col=name_col)
    print(f"  Final dataset shape: {df.shape}")

    # Remove internal tracking column
    if "_source_file" in df.columns:
        source_summary = df["_source_file"].value_counts().to_dict()
        df = df.drop(columns=["_source_file"])
    else:
        source_summary = {}

    # Save outputs
    output_csv = os.path.join(OUTPUT_DIR, "unified_products.csv")
    df.to_csv(output_csv, index=False)
    print(f"\n  Saved clean dataset: {output_csv}")

    # Save quality report
    report = {
        "files_loaded": len(datasets),
        "total_rows_raw": sum(len(d) for _, d in datasets),
        "total_rows_clean": len(df),
        "columns": list(df.columns),
        "schema_differences": schema_report,
        "missing_value_actions": missing_report,
        "fuzzy_duplicate_groups": len(dup_groups),
        "sample_duplicates": dup_groups[:10],
        "source_file_distribution": source_summary,
        "columns_dropped": dropped_cols,
    }

    return df, report


if __name__ == "__main__":
    df, report = run_pipeline()

    # Also generate the quality report
    from quality_report import generate_report
    generate_report(df, report)
