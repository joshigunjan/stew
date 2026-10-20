import json
from typing import Dict, Any
from clara.profiler.base import DatasetProfile

TYPE_MAP = {
    "numeric": "sc:Float",
    "integer": "sc:Integer",
    "categorical": "sc:Text",
    "text": "sc:Text",
    "datetime": "sc:DateTime",
    "boolean": "sc:Boolean",
    "latitude": "sc:Float",
    "longitude": "sc:Float",
}

def generate_croissant_metadata(profile: DatasetProfile) -> Dict[str, Any]:
    """
    Generates MLCommons Croissant (JSON-LD) metadata compliant with the Croissant specification.
    Includes Geocroissant extensions if the dataset has spatial properties.
    """
    file_object_id = f"{profile.dataset_id}_file"
    record_set_id = f"{profile.dataset_id}_records"
    
    # Base JSON-LD context
    context = {
        "@language": "en",
        "@vocab": "https://schema.org/",
        "citeAs": "cr:citeAs",
        "column": "cr:column",
        "cr": "http://mlcommons.org/croissant/",
        "rai": "http://mlcommons.org/croissant/rai/",
        "data": {
            "@id": "cr:data",
            "@type": "@json"
        },
        "dataType": {
            "@id": "cr:dataType",
            "@type": "@vocab"
        },
        "extract": "cr:extract",
        "field": "cr:field",
        "fileProperty": "cr:fileProperty",
        "fileObject": "cr:fileObject",
        "fileSet": "cr:fileSet",
        "format": "cr:format",
        "includes": "cr:includes",
        "isLiveDataset": "cr:isLiveDataset",
        "jsonPath": "cr:jsonPath",
        "key": "cr:key",
        "md5": "cr:md5",
        "parentField": "cr:parentField",
        "path": "cr:path",
        "recordSet": "cr:recordSet",
        "references": "cr:references",
        "regex": "cr:regex",
        "repeated": "cr:repeated",
        "replace": "cr:replace",
        "sc": "https://schema.org/",
        "separator": "cr:separator",
        "source": "cr:source",
        "subField": "cr:subField",
        "transform": "cr:transform"
    }
    
    if profile.is_spatial:
        context["geo"] = "http://www.opengis.net/ont/geosparql#"
        context["geocr"] = "http://mlcommons.org/croissant/geocroissant/"

    # Build fields for RecordSet
    fields = []
    for col_name, col in profile.columns.items():
        croissant_type = TYPE_MAP.get(col.inferred_type, "sc:Text")
        field_obj: Dict[str, Any] = {
            "@type": "cr:Field",
            "@id": f"{record_set_id}/{col_name}",
            "name": col_name,
            "description": col.suggested_description or f"Variable {col_name}",
            "dataType": croissant_type,
            "source": {
                "fileObject": {"@id": file_object_id},
                "extract": {"column": col_name}
            }
        }
        
        if col.suggested_unit:
            field_obj["unit"] = col.suggested_unit
            
        if col.missing_value_markers:
            field_obj["rai:missingValueIndicator"] = col.missing_value_markers
            
        fields.append(field_obj)

    # Build distribution (single file or collection)
    if collection_files := profile.metadata_context.get("files"):
        distribution_items = []
        for i, cf in enumerate(collection_files):
            distribution_items.append({
                "@type": "cr:FileObject",
                "@id": f"{profile.dataset_id}_file_{i}",
                "name": cf.get("name"),
                "description": f"Scientific dataset layer ({cf.get('size')})",
                "contentUrl": cf.get("url"),
                "encodingFormat": "application/x-hdf5" if cf.get("name", "").endswith(".h5") else "application/octet-stream"
            })
    else:
        distribution_items = [
            {
                "@type": "cr:FileObject",
                "@id": file_object_id,
                "name": profile.file_name,
                "description": f"Primary scientific data file in {profile.file_format.upper()} format",
                "contentUrl": profile.file_name,
                "encodingFormat": f"text/{profile.file_format}" if profile.file_format in ["csv", "tsv"] else "application/octet-stream"
            }
        ]

    croissant_doc: Dict[str, Any] = {
        "@context": context,
        "@type": "sc:Dataset",
        "name": profile.title,
        "description": f"FAIR-certified scientific dataset containing {profile.row_count:,} observations across {profile.column_count} variables. Curated with Stew, the Sovereign AI Data Steward.",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "license": f"https://spdx.org/licenses/{profile.license}.html",
        "distribution": distribution_items,
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": record_set_id,
                "name": "default",
                "description": f"Main tabular records containing {profile.row_count} rows.",
                "field": fields
            }
        ]
    }

    if doi := profile.metadata_context.get("doi"):
        croissant_doc["citeAs"] = f"https://doi.org/{doi}"
    if creators := profile.metadata_context.get("creators"):
        croissant_doc["creator"] = [{"@type": "sc:Person", "name": c} for c in creators if c]

    # Geocroissant spatial extensions
    if profile.is_spatial and profile.spatial_bbox:
        bbox = profile.spatial_bbox
        croissant_doc["spatialCoverage"] = {
            "@type": "sc:Place",
            "geo": {
                "@type": "sc:GeoShape",
                "box": f"{bbox[1]} {bbox[0]} {bbox[3]} {bbox[2]}"
            }
        }
        if profile.spatial_crs:
            croissant_doc["geocr:crs"] = profile.spatial_crs

    return croissant_doc
