# Data Quality Report
==================================================

## Summary
- **Files processed:** 21
- **Raw rows (before cleaning):** 82,105
- **Clean rows (after cleaning):** 71,481
- **Rows removed:** 10,624 (12.9%)
- **Final columns:** 6

## Schema Differences Across Source Files
- **us-shein-appliances-3987.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, color-count, product-locatelabels-img src
- **us-shein-automotive-4110.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, color-count, product-locatelabels-img src, rank-sub
- **us-shein-baby_and_maternity-4433.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, product-locatelabels-img src, rank-sub, rank-title
- **us-shein-bags_and_luggage-4299.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, product-locatelabels-img src
- **us-shein-beauty_and_health-4267.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, product-locatelabels-img src
- **us-shein-curve-2849.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, product-locatelabels-img src
- **us-shein-electronics-4395.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, product-locatelabels-img src
- **us-shein-home_and_kitchen-3719.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, color-count, goods-title-link--jump, goods-title-link--jump href
- **us-shein-home_textile-3883.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, product-locatelabels-img src
- **us-shein-jewelry_and_accessories-3548.csv** missing: blackfridaybelts-bg src, blackfridaybelts-content, color-count, product-locatelabels-img src
- ... and 11 more files

## Missing Value Treatment
| Column | Missing % | Action |
|--------|-----------|--------|
| selling_proposition | 33.79% | filled_unknown |
| discount | 33.04% | filled_unknown |
| product_name | 0.02% | filled_unknown |
| price | 0.0% | filled_median |

## Duplicate Detection
- **Fuzzy duplicate groups found:** 412
- **Sample duplicate groups:**
  1. DAZY Solid Rib Knit Thermal Underwear Vest | Dazy Star Solid Rib Knit Thermal Underwear Vest (score: 87.64044943820225)
  2. SHEIN Swim Basics Summer Beach Solid Tie Front Wide Leg Cover Up Pants | SHEIN Swim Basics Summer Beach Solid Tie Front Wide Leg Cover Up Pants (score: 100.0)
  3. SHEIN Swim Mod Summer Beach Random Floral Print Bikini Set Smocked Halter Triangle Bra Top & Tie Side Bikini Bottom 2 Piece Swimsuit | SHEIN Swim Mod Summer Beach Random Floral Print Bikini Set Smocked Halter Triangle Bra Top & Tie Side Bikini Bottom 2 Piece Swimsuit | SHEIN X Hangout Fest SHEIN Swim Mod Summer Beach Random Floral Print Bikini Set Smocked Halter Triangle Bra Top & Tie Side Bikini Bottom 2 Piece Swimsuit (score: 100.0)
  4. 2 pcs Badge Holder and 2 pcs Heavy Duty Retractable Reel, ID Badge Holders with Retractable Reel Clip for Nurse Teacher Student Office Women Men | 2 pcs Badge Holder and 2 pcs Heavy Duty Retractable Reel, ID Badge Holders withRetractable Reel Clip for Nurse Teacher Student Office Women Men (score: 91.98606271777004)
  5. 1pc Wooden Soap Dish for Shower, Shower Soap Holder, Self draining Bar Soap Holder for Bathroom, Soap Saver Soap Tray Soap Stand for Homemade Soap | 1pc Wooden Soap Dish for Shower, Shower Soap Holder, Self draining Bar Soap Holder for Bathroom, Soap Saver Soap Tray Soap Stand for Homemade Soap (score: 100.0)

## Final Data Profile
- **Shape:** 71,481 rows x 6 columns
- **Memory usage:** 30.1 MB

### Column Types
- **price** (float64): 4,327 unique, 0 null
- **discount** (object): 91 unique, 0 null
- **selling_proposition** (object): 111 unique, 0 null
- **product_name** (object): 71,481 unique, 0 null
- **source_file** (object): 21 unique, 0 null
- **category** (object): 21 unique, 0 null

