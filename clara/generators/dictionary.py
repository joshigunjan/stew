import io
import csv
from typing import Dict, Any, List
from clara.profiler.base import DatasetProfile

def generate_data_dictionary_records(profile: DatasetProfile) -> List[Dict[str, Any]]:
    records = []
    for col_name, col in profile.columns.items():
        records.append({
            "variable_name": col.name,
            "inferred_type": col.inferred_type,
            "physical_dtype": col.physical_dtype,
            "unit": col.suggested_unit or "-",
            "description": col.suggested_description or "",
            "null_count": col.null_count,
            "null_ratio": f"{int(col.null_ratio * 100)}%",
            "distinct_count": col.distinct_count,
            "min_val": str(col.min_val) if col.min_val is not None else "-",
            "max_val": str(col.max_val) if col.max_val is not None else "-",
            "missing_markers": ", ".join(col.missing_value_markers) or "None",
            "samples": ", ".join(str(s) for s in col.sample_values[:3])
        })
    return records

def generate_data_dictionary_markdown(profile: DatasetProfile) -> str:
    lines = [
        f"# Data Dictionary: {profile.title}",
        f"**File:** `{profile.file_name}` | **Rows:** {profile.row_count:,} | **Columns:** {profile.column_count}\n",
        "| Variable | Type | Unit | Description | Nulls | Range / Frequencies | Missing Codes |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for r in generate_data_dictionary_records(profile):
        val_range = f"[{r['min_val']} .. {r['max_val']}]" if r['min_val'] != "-" else r['samples']
        lines.append(
            f"| `{r['variable_name']}` | {r['inferred_type']} | {r['unit']} | {r['description']} | "
            f"{r['null_ratio']} | {val_range} | {r['missing_markers']} |"
        )
    return "\n".join(lines)

def generate_data_dictionary_csv(profile: DatasetProfile) -> str:
    records = generate_data_dictionary_records(profile)
    if not records:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()
