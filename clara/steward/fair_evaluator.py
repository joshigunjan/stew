from typing import Dict, Any, List
from clara.profiler.base import DatasetProfile

def evaluate_fair_score(profile: DatasetProfile) -> Dict[str, Any]:
    """
    Evaluates dataset against FAIR and FAIR² (AI-Readiness) criteria.
    Returns overall score (0-100), category scores, and recommendations.
    """
    scores = {
        "findable": 0,       # Max 25
        "accessible": 0,     # Max 25
        "interoperable": 0,  # Max 25
        "reusable": 0,       # Max 25
    }
    recommendations: List[str] = []
    
    # 1. Findable (Identifier, rich metadata, indexing)
    if profile.dataset_id:
        scores["findable"] += 10
    if profile.title and len(profile.title) > 3:
        scores["findable"] += 8
    if profile.summary_notes or profile.domain_field:
        scores["findable"] += 7
    else:
        recommendations.append("Specify domain keywords or a detailed description to boost Findability.")

    # 2. Accessible (Open formats, protocol)
    open_formats = ["csv", "tsv", "parquet", "json", "geojson", "netcdf", "hdf5"]
    if profile.file_format.lower() in open_formats:
        scores["accessible"] += 15
    else:
        scores["accessible"] += 5
        recommendations.append(f"Format .{profile.file_format} is proprietary; consider exporting to Parquet or CSV.")
        
    if profile.license in ["CC-BY-4.0", "CC0-1.0", "MIT", "Apache-2.0"]:
        scores["accessible"] += 10
    else:
        scores["accessible"] += 3
        recommendations.append("Attach an open science license (e.g. CC-BY-4.0) to ensure clear access rights.")

    # 3. Interoperable (Ontologies, standardized types, Croissant compatibility)
    columns_with_units = sum(1 for c in profile.columns.values() if c.suggested_unit)
    if columns_with_units >= max(1, len(profile.columns) * 0.4):
        scores["interoperable"] += 15
    else:
        scores["interoperable"] += 5
        recommendations.append("Assign physical units (QUDT) to numerical columns to ensure interoperability.")

    if profile.is_spatial:
        if profile.spatial_crs and profile.spatial_bbox:
            scores["interoperable"] += 10
        else:
            scores["interoperable"] += 5
    else:
        # Check standard typed columns
        scores["interoperable"] += 10

    # 4. Reusable (Data dictionary, missing value documentation, provenance)
    documented_cols = sum(1 for c in profile.columns.values() if c.suggested_description)
    if documented_cols >= len(profile.columns) * 0.8:
        scores["reusable"] += 15
    else:
        scores["reusable"] += 5
        recommendations.append("Review column descriptions in the Data Dictionary to assist downstream reusers.")

    # Missing value handling
    has_sentinels = any(len(c.missing_value_markers) > 0 for c in profile.columns.values())
    if not has_sentinels:
        scores["reusable"] += 10
    else:
        scores["reusable"] += 5
        recommendations.append("Confirm sentinel missing values (e.g. -999) with Stew so they are recorded in Croissant metadata.")

    total_score = sum(scores.values())
    
    return {
        "overall_score": total_score,
        "max_score": 100,
        "categories": scores,
        "ai_ready": total_score >= 80,
        "recommendations": recommendations,
        "grade": "A (AI-Ready)" if total_score >= 85 else ("B (FAIR Compliant)" if total_score >= 70 else "C (Needs Curation)")
    }
