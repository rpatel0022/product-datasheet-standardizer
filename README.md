# Product Datasheet Standardizer

A data cleaning pipeline that takes **82,000+ messy product records** from **21 different CSV files** — each with a different schema — and produces a single, clean, unified dataset. Detects schema differences, standardizes naming conventions, drops useless columns, handles missing values intelligently, and identifies duplicate products using fuzzy string matching.

## Problem

Product data from e-commerce platforms is messy. Different category pages export different column sets. The same information appears under different names (`goods-title-link` vs `goods-title-link--jump`). Prices have currency symbols embedded as strings. Near-identical products appear multiple times with slightly different names.

This pipeline solves all of that — the same kind of work needed to migrate scattered datasheets into a unified template.

## Dataset

**Source:** [SHEIN E-Commerce Data (Kaggle)](https://www.kaggle.com/datasets/oleksiimartusiuk/e-commerce-data-shein) — 21 CSV files, one per product category (Appliances, Electronics, Shoes, etc.), with 80,000+ total product listings.

**Raw data characteristics:**
- 21 files with **different column sets** (7-12 columns each, 12 unique columns across all files)
- Product names in two different columns (`goods-title-link` for short names, `goods-title-link--jump` for full names)
- Prices stored as strings with `$` prefix (e.g., `"$2.03"`)
- Discounts stored as strings (e.g., `"-22%"`)
- Many columns only exist in a few files (e.g., `blackfridaybelts-bg src` only appears in 2 out of 21 files)

## Pipeline Architecture

```
21 Raw CSVs ──> Load & Merge ──> Standardize Names ──> Clean Types
                                                            │
Output <── Dedup <── Handle Nulls <── Drop Junk Columns <───┘
```

### Step 1: Load & Merge (21 files → 82,105 rows)

- Recursively finds all `.csv` files in the `data/` directory
- Loads each file, tags rows with `_source_file` for traceability
- Detects **schema differences** by computing the union of all column sets and reporting what each file is missing
- Concatenates everything into a single DataFrame using `pd.concat` with column alignment

### Step 2: Standardize Column Names

Two-pass normalization:

**Pass 1 — Syntactic cleanup:**
- Lowercase all names
- Replace non-alphanumeric characters with underscores
- Strip leading/trailing underscores

**Pass 2 — Semantic synonym resolution:**
- Maps known aliases to canonical names using a configurable synonym dictionary
- `goods_title_link` → `product_name` (short name, 99.98% populated)
- `goods_title_link_jump` → `product_name_full` (long name, only ~1% populated)
- Coalesces the two: uses the short name, fills gaps from the full name
- Handles duplicate columns after renaming (keeps first)

### Step 3: Clean Data Types & Extract Categories

- **Prices:** Strips currency symbols (`$`, `€`) and non-numeric characters via regex, converts to `float64`
- **Ratings:** Converts to numeric, clamps to valid 0-5 range (values outside this become NaN)
- **Category extraction:** Parses the source filename to derive category — `us-shein-electronics-4395.csv` becomes `Electronics`. This adds structured metadata that didn't exist in the raw data.
- **Text fields:** Strips whitespace, normalizes `"nan"` strings back to actual NaN

### Step 4: Drop Near-Empty Columns (13 → 6 columns)

Columns with **>70% null values** only existed in a few source files and add noise to a unified dataset. The pipeline logs what it drops, then removes them:

| Column Dropped | Null % | Reason |
|----------------|--------|--------|
| `product_url` | 99.2% | Only populated for ~650 featured products |
| `rank` | 82.2% | Only in files that had bestseller rankings |
| `rank_detail` | 82.2% | Subcategory rank info, same sparse pattern |
| `color_count` | 76.0% | Only tracked for fashion categories |
| `blackfridaybelts_bg_src` | 95.4% | Promo UI element, not product data |
| `blackfridaybelts_content` | 95.4% | Promo UI element, not product data |
| `product_locatelabels_img_src` | 95.6% | UI badge images, not product data |

**Why 70%?** Below that, columns are useful enough to keep with imputation. Above that, you're inventing data for the majority of rows. The threshold is configurable via `DROP_THRESHOLD`.

### Step 5: Handle Missing Values

Strategy depends on column type and missing percentage:

| Column Type | Missing < 30% | Missing 30-50% | Missing > 50% |
|-------------|---------------|-----------------|----------------|
| **Numeric** | Fill with **median** (robust to skewed distributions like price data) | Left as NaN | Left as NaN |
| **Categorical** | Fill with `"Unknown"` | Fill with `"Unknown"` | Left as NaN |

**Why median instead of mean for price?** Prices are right-skewed (many cheap items, few expensive ones). Mean = $4.50, Median = $3.20 — median better represents the typical product.

### Step 6: Fuzzy Deduplication

**Exact dedup:** `drop_duplicates()` on `product_name` — removes 10,624 rows where the same product appears in multiple category pages.

**Fuzzy dedup:** Uses `rapidfuzz.fuzz.token_sort_ratio` to find near-duplicate names:
- Tokenizes both strings, sorts tokens alphabetically, then computes similarity ratio
- This handles word reordering: "Blue Cotton T-Shirt Large" matches "Large Blue T-Shirt Cotton"
- **Threshold: 85** — tested 80 (too many false positives from generic names like "1pc Storage Box") and 90 (missed obvious dupes)
- For datasets >10,000 names, samples 10,000 randomly to keep runtime under 2 minutes

**Example duplicates found:**
| Product A | Product B | Score |
|-----------|-----------|-------|
| "Stainless Steel Visual Kitchen Timer With Magnetic Back **Countdown Reminder**" | "Stainless Steel Visual Kitchen Timer With Magnetic Back, **Countdown Cooking Timer**" | 87.2% |
| "Men's **Contrast Color Short Sleeve** Polo Shirt" | "Men's **Contrast Color Trim** Polo Shirt" | 85.7% |

## Results

| Metric | Before | After |
|--------|--------|-------|
| Source files | 21 | 1 unified CSV |
| Total rows | 82,105 | 71,481 |
| Columns | 12 (inconsistent) | 6 (clean) |
| Null values | 543,000+ | Minimal (imputed or dropped) |
| Exact duplicates | 10,624 | Removed |
| Fuzzy duplicate groups | ~400 | Identified and logged |
| Categories | Implicit in filenames | Explicit column (21 categories) |

## Project Structure

```
project1_datasheet_standardizer/
├── standardizer.py          # Main pipeline — run this
├── quality_report.py        # Generates markdown + JSON quality reports
├── requirements.txt         # Python dependencies
├── data/                    # Raw Kaggle CSVs (not committed)
├── output/
│   ├── unified_products.csv           # Full cleaned dataset
│   ├── sample_unified_products.csv    # First 100 rows for quick inspection
│   ├── quality_report.md             # Human-readable report
│   └── quality_report.json           # Machine-readable report
└── docs/
    └── index.html           # GitHub Pages dashboard
```

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download the dataset from Kaggle
kaggle datasets download -d oleksiimartusiuk/e-commerce-data-shein --unzip -p data/

# 3. Run the pipeline
python standardizer.py
```

The pipeline prints progress at each step and generates all output files automatically.

## Tech Stack

| Library | Purpose |
|---------|---------|
| `pandas` | Data loading, merging, manipulation, type conversion |
| `rapidfuzz` | Fuzzy string matching for duplicate detection (`token_sort_ratio` scorer) |
| `numpy` | Numeric operations, NaN handling |

## Configuration

Key parameters in `standardizer.py` that can be tuned:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `FUZZY_THRESHOLD` | 85 | Minimum similarity score to flag as duplicate |
| `DROP_THRESHOLD` | 0.70 | Null fraction above which columns get dropped |
| `MAX_DEDUP_CHECK` | 10,000 | Sample size for fuzzy matching (performance) |
