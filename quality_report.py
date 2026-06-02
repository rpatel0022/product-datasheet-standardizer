"""
Quality Report Generator
========================
Produces a human-readable data quality report summarizing
what the standardizer found and fixed.
"""

import os
import json
import pandas as pd

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def generate_report(df, pipeline_report):
    """Generate a markdown quality report from pipeline results."""
    lines = []
    lines.append("# Data Quality Report")
    lines.append("=" * 50)
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append(f"- **Files processed:** {pipeline_report['files_loaded']}")
    lines.append(f"- **Raw rows (before cleaning):** {pipeline_report['total_rows_raw']:,}")
    lines.append(f"- **Clean rows (after cleaning):** {pipeline_report['total_rows_clean']:,}")
    rows_removed = pipeline_report["total_rows_raw"] - pipeline_report["total_rows_clean"]
    lines.append(f"- **Rows removed:** {rows_removed:,} ({rows_removed/max(pipeline_report['total_rows_raw'],1)*100:.1f}%)")
    lines.append(f"- **Final columns:** {len(pipeline_report['columns'])}")
    lines.append("")

    # Schema Differences
    lines.append("## Schema Differences Across Source Files")
    if pipeline_report["schema_differences"]:
        for diff in pipeline_report["schema_differences"][:10]:
            lines.append(f"- **{diff['file']}** missing: {', '.join(diff['missing_columns'][:5])}")
        if len(pipeline_report["schema_differences"]) > 10:
            lines.append(f"- ... and {len(pipeline_report['schema_differences']) - 10} more files")
    else:
        lines.append("- All files share the same schema")
    lines.append("")

    # Missing Values
    lines.append("## Missing Value Treatment")
    lines.append("| Column | Missing % | Action |")
    lines.append("|--------|-----------|--------|")
    for col, info in sorted(
        pipeline_report["missing_value_actions"].items(),
        key=lambda x: x[1]["pct"],
        reverse=True,
    ):
        lines.append(f"| {col} | {info['pct']}% | {info['action']} |")
    lines.append("")

    # Duplicates
    lines.append("## Duplicate Detection")
    lines.append(f"- **Fuzzy duplicate groups found:** {pipeline_report['fuzzy_duplicate_groups']}")
    if pipeline_report["sample_duplicates"]:
        lines.append("- **Sample duplicate groups:**")
        for i, group in enumerate(pipeline_report["sample_duplicates"][:5]):
            names = group["names"][:3]
            lines.append(f"  {i+1}. {' | '.join(names)} (score: {group['score']})")
    lines.append("")

    # Data Profile
    lines.append("## Final Data Profile")
    lines.append(f"- **Shape:** {df.shape[0]:,} rows x {df.shape[1]} columns")
    lines.append(f"- **Memory usage:** {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
    lines.append("")

    # Column types
    lines.append("### Column Types")
    for col in df.columns:
        n_unique = df[col].nunique()
        n_null = df[col].isna().sum()
        lines.append(f"- **{col}** ({df[col].dtype}): {n_unique:,} unique, {n_null:,} null")
    lines.append("")

    # Source file distribution
    if pipeline_report.get("source_file_distribution"):
        lines.append("## Source File Distribution")
        for fname, count in sorted(
            pipeline_report["source_file_distribution"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:15]:
            lines.append(f"- {fname}: {count:,} rows")
    lines.append("")

    report_text = "\n".join(lines)

    # Save as markdown
    report_path = os.path.join(OUTPUT_DIR, "quality_report.md")
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\n  Saved quality report: {report_path}")

    # Also save raw report as JSON
    json_path = os.path.join(OUTPUT_DIR, "quality_report.json")
    # Convert non-serializable items
    serializable = {k: v for k, v in pipeline_report.items()}
    with open(json_path, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"  Saved JSON report: {json_path}")

    return report_text
