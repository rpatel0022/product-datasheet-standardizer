# Product Datasheet Standardizer

Takes 21 messy product CSV files (80,000+ records) and produces a single, clean, unified dataset.

## What it does

1. **Merges 21 CSV files** with different schemas into one unified dataset
2. **Standardizes column names** (normalizes synonyms, cleans formatting)
3. **Extracts categories** from source file names
4. **Drops near-empty columns** (>70% null) that only existed in a few source files
5. **Handles missing values** (median for numeric, mode for categorical)
6. **Fuzzy deduplication** using rapidfuzz token sort ratio (found 400+ duplicate groups)
7. **Generates a quality report** with schema differences, missing value treatment, and duplicate analysis

## Results

| Metric | Value |
|--------|-------|
| Files processed | 21 |
| Raw rows | 82,105 |
| Clean rows | 71,481 |
| Columns dropped (>70% null) | 7 |
| Final clean columns | 6 |
| Duplicates removed | 10,624 (12.9%) |
| Fuzzy duplicate groups | ~400 |
| Categories extracted | 21 |

## Key design decisions

- **Fuzzy threshold = 85**: tested 80 (too many false positives from generic names) and 90 (missed obvious dupes like "Kitchen Timer Countdown Reminder" vs "Kitchen Timer Countdown Cooking")
- **Drop >70% null columns**: columns like `product_url` (99% null) and `blackfridaybelts_bg_src` (95% null) only existed in a few source files and add noise to the unified dataset
- **Median fill for price** instead of mean: prices are right-skewed, median is more representative

## Run it

```bash
pip install -r requirements.txt

# Download data from Kaggle:
# kaggle datasets download -d oleksiimartusiuk/e-commerce-data-shein --unzip -p data/

python standardizer.py
```

## Output

- `output/unified_products.csv` -- clean, deduplicated dataset
- `output/sample_unified_products.csv` -- first 100 rows for quick inspection
- `output/quality_report.md` -- human-readable quality report
- `output/quality_report.json` -- machine-readable report

## Tech

`pandas`, `rapidfuzz`, `numpy`
