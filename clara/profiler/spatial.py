import json
from pathlib import Path
from typing import Optional
import pandas as pd

from clara.profiler.base import DatasetProfile
from clara.profiler.tabular import profile_dataframe

def profile_geojson(file_path: Path, dataset_id: str) -> Optional[DatasetProfile]:
    """
    Profiles GeoJSON datasets, extracting geometry types, bounding boxes, and tabular feature properties.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        features = data.get("features", [])
        if not features:
            return None
            
        # Extract properties into a dataframe
        records = []
        lons = []
        lats = []
        geom_types = set()
        
        for feat in features:
            props = feat.get("properties", {}) or {}
            geom = feat.get("geometry", {}) or {}
            geom_type = geom.get("type", "Unknown")
            geom_types.add(geom_type)
            
            coords = geom.get("coordinates")
            if geom_type == "Point" and coords and len(coords) >= 2:
                lons.append(coords[0])
                lats.append(coords[1])
                props["_geometry_type"] = "Point"
                props["_lon"] = coords[0]
                props["_lat"] = coords[1]
            else:
                props["_geometry_type"] = geom_type
                
            records.append(props)
            
        df = pd.DataFrame(records)
        profile = profile_dataframe(df, file_path, dataset_id)
        
        profile.is_spatial = True
        profile.file_format = "geojson"
        profile.spatial_crs = "EPSG:4326"
        
        if lons and lats:
            profile.spatial_bbox = [
                round(min(lons), 4),
                round(min(lats), 4),
                round(max(lons), 4),
                round(max(lats), 4)
            ]
            
        profile.summary_notes.append(
            f"GeoJSON FeatureCollection with {len(features)} features. Geometries: {', '.join(geom_types)}."
        )
        return profile
    except Exception as e:
        return None
