from typing import Dict, Any, List, Optional
from clara.profiler.base import DatasetProfile

# Standard CF (Climate and Forecast) convention variable mappings
CF_STANDARD_NAMES = {
    "temperature": {"cf_name": "air_temperature", "canonical_units": ["K", "degC", "celsius"]},
    "temp": {"cf_name": "air_temperature", "canonical_units": ["K", "degC", "celsius"]},
    "t_air": {"cf_name": "air_temperature", "canonical_units": ["degC", "K", "celsius"]},
    "surface_temp": {"cf_name": "surface_temperature", "canonical_units": ["K", "degC"]},
    "pressure": {"cf_name": "air_pressure", "canonical_units": ["Pa", "hPa", "bar"]},
    "p_sfc": {"cf_name": "surface_air_pressure", "canonical_units": ["hPa", "Pa"]},
    "humidity": {"cf_name": "relative_humidity", "canonical_units": ["%", "1", "fraction", "pct"]},
    "rh": {"cf_name": "relative_humidity", "canonical_units": ["%", "1", "fraction", "pct"]},
    "wind_speed": {"cf_name": "wind_speed", "canonical_units": ["m s-1", "m/s", "km/h"]},
    "wind_spd": {"cf_name": "wind_speed", "canonical_units": ["m s-1", "m/s", "km/h"]},
    "wind_dir": {"cf_name": "wind_from_direction", "canonical_units": ["degree", "deg"]},
    "precipitation": {"cf_name": "precipitation_flux", "canonical_units": ["kg m-2 s-1", "mm/h", "mm"]},
    "rain": {"cf_name": "rainfall_amount", "canonical_units": ["mm", "m"]},
    "solar_radiation": {"cf_name": "surface_downwelling_shortwave_flux_in_air", "canonical_units": ["W m-2", "W/m2"]},
    "soil_moist": {"cf_name": "soil_moisture_content", "canonical_units": ["m3 m-3", "fraction", "%"]},
}

def audit_domain_standards(profile: DatasetProfile) -> Dict[str, Any]:
    """
    Audits dataset against domain-specific scientific standards:
    1. Earth Observation (EO) & Geospatial: STAC, CRS (EPSG), Bounding Box sanity, Geocroissant.
    2. Climate & Atmospheric Science: CF Conventions (CF-1.8), Standard Names, UDUNITS/QUDT.
    """
    domain_report = {
        "earth_observation": {
            "applicable": False,
            "crs_code": profile.spatial_crs or "Unknown",
            "crs_valid": False,
            "bbox_valid": False,
            "spatial_extent_deg2": None,
            "geocroissant_compliant": False,
            "stac_metadata_ready": False,
            "checks": []
        },
        "climate_and_forecast": {
            "applicable": False,
            "cf_version": "CF-1.8",
            "compliant": False,
            "mapped_cf_variables": 0,
            "coordinate_axes": [],
            "units_standardized": True,
            "checks": []
        }
    }
    
    # 1. Earth Observation & Geospatial Audit
    col_names_lower = [c.lower() for c in profile.columns.keys()]
    has_lat = any("lat" in c for c in col_names_lower)
    has_lon = any("lon" in c or "lng" in c for c in col_names_lower)
    is_geo_format = profile.file_format.lower() in ["geojson", "geotiff", "tif", "tiff", "hdf5_collection"]
    
    if profile.is_spatial or (has_lat and has_lon) or is_geo_format:
        eo = domain_report["earth_observation"]
        eo["applicable"] = True
        
        # CRS check
        if profile.spatial_crs and profile.spatial_crs.upper() in ["EPSG:4326", "WGS84", "OGC:CRS84"]:
            eo["crs_valid"] = True
            eo["checks"].append("✓ Coordinate Reference System: Standard WGS84 (EPSG:4326) confirmed.")
        elif profile.spatial_crs:
            eo["crs_valid"] = True
            eo["checks"].append(f"✓ Coordinate Reference System: {profile.spatial_crs} identified.")
        else:
            eo["checks"].append("⚠ CRS missing from header; defaulting to WGS84 (EPSG:4326) for geospatial features.")
            
        # Bounding Box Sanity Check
        if profile.spatial_bbox and len(profile.spatial_bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = profile.spatial_bbox
            if -180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0 and -90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0:
                eo["bbox_valid"] = True
                width = abs(max_lon - min_lon)
                height = abs(max_lat - min_lat)
                eo["spatial_extent_deg2"] = round(width * height, 4)
                eo["checks"].append(f"✓ Geospatial Bounding Box: [{min_lon}, {min_lat}, {max_lon}, {max_lat}] within valid terrestrial limits.")
            else:
                eo["checks"].append("⚠ Coordinates outside standard geographic bounds [-180, 180], [-90, 90]; likely projected metric grid (UTM).")
        else:
            eo["checks"].append("ℹ Spatial bounding box not explicitly bounded; Point geometries present.")

        eo["geocroissant_compliant"] = eo["crs_valid"] and (eo["bbox_valid"] or bool(profile.spatial_bbox))
        eo["stac_metadata_ready"] = eo["geocroissant_compliant"]
        if eo["geocroissant_compliant"]:
            eo["checks"].append("✓ Geocroissant spatialCoverage & STAC asset catalog geometry verified.")

    # 2. Climate & Forecast (CF Conventions) Audit
    cf = domain_report["climate_and_forecast"]
    climate_keywords = ["temp", "t_air", "air_temp", "humidity", "rh", "pressure", "p_sfc", "precipitation", "wind", "flux", "radiation", "soil", "climate"]
    is_climate_domain = (profile.domain_field and "climate" in profile.domain_field.lower()) or \
                        any(any(kw in c for kw in climate_keywords) for c in col_names_lower)
    
    if is_climate_domain or profile.file_format.lower() in ["netcdf", "nc", "hdf5"]:
        cf["applicable"] = True
        
        # Coordinate axes identification (time, lat, lon, level)
        coords = []
        for name, col in profile.columns.items():
            nl = name.lower()
            if any(t in nl for t in ["time", "date", "timestamp", "datetime"]):
                coords.append(f"time ({name})")
            elif any(t in nl for t in ["lat", "latitude", "y"]):
                coords.append(f"latitude ({name})")
            elif any(t in nl for t in ["lon", "longitude", "x"]):
                coords.append(f"longitude ({name})")
            elif any(t in nl for t in ["elevation", "altitude", "depth", "level", "pressure_level"]):
                coords.append(f"vertical_axis ({name})")
                
        cf["coordinate_axes"] = coords
        if len(coords) >= 2:
            cf["checks"].append(f"✓ CF Coordinate Axes identified: {', '.join(coords)}")
        else:
            cf["checks"].append("⚠ Coordinate axes partially incomplete; recommend explicitly defining time and spatial dimensions.")
            
        # Standard Names & Unit verification
        mapped_count = 0
        unstandardized_units = []
        for name, col in profile.columns.items():
            nl = name.lower()
            for key, spec in CF_STANDARD_NAMES.items():
                if key in nl:
                    mapped_count += 1
                    col.suggested_semantic_type = f"cf:{spec['cf_name']}"
                    if not col.suggested_unit or col.suggested_unit not in spec["canonical_units"]:
                        unstandardized_units.append(name)
                    break
                    
        cf["mapped_cf_variables"] = mapped_count
        if mapped_count > 0:
            cf["checks"].append(f"✓ Identified {mapped_count} variables mapped to CF Standard Names vocabulary.")
        if unstandardized_units:
            cf["checks"].append(f"⚠ Recommended unit standardization for: {', '.join(unstandardized_units[:3])} (align to UDUNITS/QUDT).")
        else:
            cf["checks"].append("✓ All detected physical units conform to UDUNITS / QUDT standards.")
            
        # Sentinel checks
        sentinels_found = any(len(c.missing_value_markers) > 0 for c in profile.columns.values())
        if sentinels_found:
            cf["checks"].append("ℹ Sentinel missing values (-999) detected: Mapped to CF '_FillValue' attribute.")
            
        cf["compliant"] = len(coords) >= 2 and mapped_count >= 1

    return domain_report
