# Product Datasheet Standardizer

Takes 21 messy product CSV files (80,000+ records) and produces a single, clean, unified dataset.

**Interview story:** "I took 80,000+ messy product records from 21 different source files and built a pipeline that standardizes formats, deduplicates entries, and produces clean, unified output -- exactly what you'd need for datasheet migration."

## What it does

1. **Merges 21 CSV files** with different schemas into one unified dataset
2. **Standardizes column names** (normalizes synonyms, cleans formatting)
3. **Extracts categories** from source file names
4. **Handles missing values** (median for numeric, mode for categorical, flagging for high-null columns)
5. **Fuzzy deduplication** using rapidfuzz token sort ratio (found 400+ duplicate groups)
6. **Generates a quality report** with schema differences, missing value treatment, and duplicate analysis

## Results

| Metric | Value |
|--------|-------|
| Files processed | 21 |
| Raw rows | 82,105 |
| Clean rows | 71,481 |
| Duplicates removed | 10,624 (12.9%) |
| Fuzzy duplicate groups | ~400 |
| Categories extracted | 21 |

## Run it

```bash
# Download data from Kaggle first:
# kaggle datasets download -d oleksiimartusiuk/e-commerce-data-shein --unzip -p data/

python standardizer.py
```

## Output

- `output/unified_products.csv` -- clean, deduplicated dataset
- `output/quality_report.md` -- human-readable quality report
- `output/quality_report.json` -- machine-readable report

## Tech

`pandas`, `rapidfuzz`, `numpy`
