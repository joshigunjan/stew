import math
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from clara.profiler.base import ColumnProfile, DatasetProfile

COMMON_NA_VALUES = ["", " ", "na", "n/a", "null", "none", "nan", "-999", "-9999", "9999", "-999.0", "-9999.0", "."]

def detect_column_semantic_type(col_name: str, dtype_str: str, sample_vals: List[Any]) -> tuple[str, str, str]:
    """
    Returns (semantic_type, suggested_unit, suggested_description) based on column name heuristics.
    """
    name_lower = col_name.lower().strip()
    
    # Coordinate detection
    if any(k in name_lower for k in ["latitude", "lat", "y_coord"]):
        return "latitude", "degrees_north", "Latitude coordinate (WGS84)"
    if any(k in name_lower for k in ["longitude", "lon", "lng", "x_coord"]):
        return "longitude", "degrees_east", "Longitude coordinate (WGS84)"
    if any(k in name_lower for k in ["altitude", "elevation", "elev", "alt"]):
        return "elevation", "m", "Elevation or altitude above sea level"
        
    # Temporal detection
    if any(k in name_lower for k in ["timestamp", "date", "time", "datetime", "epoch"]):
        return "temporal", "ISO-8601", "Date or timestamp of measurement observation"
        
    # Temperature
    if any(k in name_lower for k in ["temp", "temperature", "degc", "t_air", "t_soil"]):
        unit = "degC" if "c" in name_lower else ("K" if "k" in name_lower else "degC")
        return "temperature", unit, "Observed temperature"
        
    # Pressure
    if any(k in name_lower for k in ["pressure", "pres", "hpa", "bar"]):
        return "pressure", "hPa", "Atmospheric or hydrostatic pressure"
        
    # Moisture / Humidity
    if any(k in name_lower for k in ["humidity", "rh", "moist", "moisture"]):
        return "relative_humidity", "%", "Relative humidity or moisture fraction"
        
    # Wind
    if any(k in name_lower for k in ["wind", "speed", "velocity", "ws"]):
        return "wind_speed", "m/s", "Wind velocity or speed"
        
    # Identifier
    if any(k in name_lower for k in ["id", "uuid", "station", "sensor", "device", "code"]):
        return "identifier", "", "Unique observation or sensor identifier"

    if "int" in dtype_str or "float" in dtype_str:
        return "numeric_measurement", "", f"Continuous or discrete measurement: {col_name}"
        
    return "categorical_or_text", "", f"Descriptive categorical attribute: {col_name}"

def profile_dataframe(df: pd.DataFrame, file_path: Path, dataset_id: str) -> DatasetProfile:
    total_rows = len(df)
    columns_profile: Dict[str, ColumnProfile] = {}
    
    is_spatial = False
    bbox = None
    lat_col = None
    lon_col = None

    for col in df.columns:
        s = df[col]
        dtype_str = str(s.dtype)
        
        # Calculate nulls (standard nulls + common scientific sentinel values)
        null_mask = s.isna()
        null_count = int(null_mask.sum())
        
        # Detect sentinel missing values
        sentinel_markers = []
        val_strs = s.dropna().astype(str).str.lower().str.strip()
        for marker in COMMON_NA_VALUES:
            if marker and marker in ["-999", "-9999", "-999.0", "-9999.0"]:
                if (val_strs == marker).any():
                    sentinel_markers.append(marker)

        non_null_s = s.dropna()
        distinct_count = int(non_null_s.nunique())
        
        # Determine high-level inferred type
        if pd.api.types.is_numeric_dtype(s):
            inferred_type = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            inferred_type = "datetime"
        elif pd.api.types.is_bool_dtype(s):
            inferred_type = "boolean"
        elif distinct_count < min(20, max(5, total_rows * 0.05)):
            inferred_type = "categorical"
        else:
            inferred_type = "text"

        # Statistics
        min_val = None
        max_val = None
        mean_val = None
        std_val = None
        
        if pd.api.types.is_numeric_dtype(s) and not non_null_s.empty:
            try:
                min_v = non_null_s.min()
                max_v = non_null_s.max()
                mean_v = non_null_s.mean()
                std_v = non_null_s.std()
                min_val = float(min_v) if not math.isnan(min_v) else None
                max_val = float(max_v) if not math.isnan(max_v) else None
                mean_val = float(mean_v) if not math.isnan(mean_v) else None
                std_val = float(std_v) if not math.isnan(std_v) else None
            except Exception:
                pass

        # Sample values (up to 5 unique clean samples)
        sample_values = non_null_s.drop_duplicates().head(5).tolist()
        # Ensure json serializable
        sample_values = [str(v) if isinstance(v, (pd.Timestamp, np.generic)) else v for v in sample_values]

        # Top frequent
        top_frequent = None
        if inferred_type in ["categorical", "text"] or distinct_count < 10:
            top_counts = non_null_s.value_counts().head(5).to_dict()
            top_frequent = {str(k): int(v) for k, v in top_counts.items()}

        semantic_type, unit, description = detect_column_semantic_type(col, dtype_str, sample_values)

        if semantic_type == "latitude":
            lat_col = col
        elif semantic_type == "longitude":
            lon_col = col

        col_prof = ColumnProfile(
            name=col,
            inferred_type=inferred_type,
            physical_dtype=dtype_str,
            total_count=total_rows,
            null_count=null_count,
            null_ratio=round(null_count / max(1, total_rows), 4),
            distinct_count=distinct_count,
            is_unique=(distinct_count == total_rows and null_count == 0),
            sample_values=sample_values,
            min_val=min_val,
            max_val=max_val,
            mean_val=mean_val,
            std_val=std_val,
            top_frequent=top_frequent,
            suggested_semantic_type=semantic_type,
            suggested_unit=unit,
            suggested_description=description,
            missing_value_markers=sentinel_markers
        )
        columns_profile[col] = col_prof

    # Check spatial bounds if lat/lon found
    if lat_col and lon_col:
        try:
            lats = pd.to_numeric(df[lat_col], errors='coerce').dropna()
            lons = pd.to_numeric(df[lon_col], errors='coerce').dropna()
            if not lats.empty and not lons.empty:
                is_spatial = True
                bbox = [
                    round(float(lons.min()), 4),
                    round(float(lats.min()), 4),
                    round(float(lons.max()), 4),
                    round(float(lats.max()), 4)
                ]
        except Exception:
            pass

    # Preview rows (first 10 rows converted to dict)
    preview_df = df.head(10).copy()
    preview_rows = []
    for record in preview_df.to_dict(orient="records"):
        clean_record = {}
        for k, v in record.items():
            if pd.isna(v):
                clean_record[k] = None
            elif isinstance(v, (pd.Timestamp, np.generic)):
                clean_record[k] = str(v)
            else:
                clean_record[k] = v
        preview_rows.append(clean_record)

    summary_notes = []
    if sentinel_count := sum(len(c.missing_value_markers) for c in columns_profile.values()):
        summary_notes.append(f"Detected potential sentinel missing value markers (-999 / -9999) across columns.")
    if is_spatial:
        summary_notes.append(f"Detected spatial coordinates: Bounding box [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}] (EPSG:4326).")

    return DatasetProfile(
        dataset_id=dataset_id,
        title=file_path.stem.replace("_", " ").title(),
        file_name=file_path.name,
        file_format=file_path.suffix.lstrip(".").lower(),
        file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
        row_count=total_rows,
        column_count=len(df.columns),
        columns=columns_profile,
        preview_rows=preview_rows,
        summary_notes=summary_notes,
        is_spatial=is_spatial,
        spatial_bbox=bbox,
        spatial_crs="EPSG:4326" if is_spatial else None
    )
