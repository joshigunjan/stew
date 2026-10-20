from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field

class ColumnProfile(BaseModel):
    name: str
    inferred_type: str  # numeric, categorical, text, datetime, boolean, coordinates
    physical_dtype: str
    total_count: int
    null_count: int
    null_ratio: float
    distinct_count: int
    is_unique: bool
    sample_values: List[Any] = Field(default_factory=list)
    min_val: Optional[Any] = None
    max_val: Optional[Any] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    top_frequent: Optional[Dict[str, int]] = None
    
    # Inferred / AI Steward attributes with explicit provenance
    suggested_semantic_type: Optional[str] = None
    suggested_unit: Optional[str] = None
    suggested_description: Optional[str] = None
    missing_value_markers: List[str] = Field(default_factory=list)
    
    # Provenance & Uncertainty Tracking (ChatGPT Recommendation 3)
    # Types: EXTRACTED_FROM_DATA, DOC_INFERRED, AI_SUGGESTED_BLABLADOR, USER_VERIFIED
    provenance_type: str = "EXTRACTED_FROM_DATA"
    provenance_evidence: str = "Extracted directly from raw dataset observation records"
    confidence_score: float = 1.0
    user_confirmed: bool = False

class DatasetProfile(BaseModel):
    dataset_id: str
    title: str = "Research Dataset"
    file_name: str
    file_format: str
    file_size_bytes: int
    row_count: int
    column_count: int
    columns: Dict[str, ColumnProfile] = Field(default_factory=dict)
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list)
    summary_notes: List[str] = Field(default_factory=list)
    
    # Geospatial & Multi-dimensional extensions
    is_spatial: bool = False
    spatial_bbox: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    spatial_crs: Optional[str] = None
    
    # Domain-specific standards audit (Earth Observation, CF Conventions - Recommendation 2)
    domain_standards: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata context provided by researcher, Zenodo, or inferred
    metadata_context: Dict[str, Any] = Field(default_factory=dict)
    domain_field: Optional[str] = None
    license: str = "CC-BY-4.0"
    created_at: str = ""
    fair_score: Optional[int] = None
    steward_assessment: Optional[str] = None
