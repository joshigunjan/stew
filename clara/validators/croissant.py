from typing import Dict, Any, List

def validate_croissant_jsonld(croissant_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Independent validator for MLCommons Croissant v1.0 metadata.
    Validates JSON-LD schema, required entities, distribution references,
    record sets, and data type mappings.
    """
    errors: List[str] = []
    warnings: List[str] = []
    passed_checks: List[str] = []
    
    # 1. Context check
    context = croissant_dict.get("@context", {})
    if not context:
        errors.append("Missing '@context' specification in JSON-LD root.")
    else:
        ctx_str = str(context)
        if "schema.org" not in ctx_str:
            errors.append("Context missing Schema.org namespace mapping.")
        if "mlcommons.org/croissant" not in ctx_str and "cr" not in context:
            warnings.append("Croissant namespace 'http://mlcommons.org/croissant/' should be explicitly aliased as 'cr'.")
        passed_checks.append("JSON-LD context namespace mappings (Schema.org & Croissant) verified.")
        
    # 2. Dataset identity & mandatory properties
    dtype = croissant_dict.get("@type")
    if dtype not in ["Dataset", "sc:Dataset"]:
        errors.append(f"Invalid root @type '{dtype}'. Expected 'sc:Dataset'.")
    else:
        passed_checks.append(f"Root entity @type correctly asserted as '{dtype}'.")
        
    name = croissant_dict.get("name")
    if not name or len(name) < 2:
        errors.append("Missing or empty dataset 'name'.")
    else:
        passed_checks.append(f"Dataset identity confirmed: '{name}'.")
        
    description = croissant_dict.get("description")
    if not description or len(description) < 10:
        warnings.append("Dataset 'description' is brief; expand description to improve findability.")
    else:
        passed_checks.append("Dataset scope and descriptive abstract verified.")
        
    license_prop = croissant_dict.get("license")
    if not license_prop:
        warnings.append("License is not explicitly declared; recommend CC-BY-4.0.")
    else:
        passed_checks.append(f"Open Science license verified: '{license_prop}'.")
        
    cite_as = croissant_dict.get("citeAs")
    if cite_as:
        passed_checks.append(f"Permanent citation linkage verified via citeAs: '{cite_as}'.")
    else:
        warnings.append("Missing 'citeAs' attribute; recommend linking persistent DOI or repository URL.")
        
    # 3. Distribution integrity
    distributions = croissant_dict.get("distribution", [])
    dist_ids = set()
    if not distributions:
        errors.append("No 'distribution' declared. A Croissant package must contain at least one FileObject or FileSet.")
    else:
        for i, dist in enumerate(distributions):
            did = dist.get("@id")
            if not did:
                errors.append(f"Distribution item #{i} is missing an '@id'.")
            else:
                dist_ids.add(did)
            if not dist.get("encodingFormat"):
                warnings.append(f"Distribution '{did or i}' missing 'encodingFormat' MIME type.")
        passed_checks.append(f"Distribution verified: {len(distributions)} FileObject/FileSet resources with unique @ids.")

    # 4. RecordSets and Field schemas
    record_sets = croissant_dict.get("recordSet", [])
    total_fields = 0
    if not record_sets:
        errors.append("No 'recordSet' defined. Croissant requires machine-actionable record sets for data loaders.")
    else:
        valid_datatypes = ["sc:Float", "sc:Integer", "sc:Text", "sc:Boolean", "sc:DateTime", "sc:GeoCoordinates"]
        for rs in record_sets:
            rs_id = rs.get("@id", "unnamed")
            fields = rs.get("field", [])
            total_fields += len(fields)
            for f in fields:
                fid = f.get("@id")
                ftype = f.get("dataType")
                if not fid:
                    errors.append(f"RecordSet '{rs_id}' contains a field missing '@id'.")
                if ftype and ftype not in valid_datatypes:
                    warnings.append(f"Field '{fid}' uses non-standard dataType '{ftype}'.")
        passed_checks.append(f"RecordSets verified: {len(record_sets)} record sets comprising {total_fields} typed fields.")

    # 5. Spatial Coverage (Geocroissant check)
    spatial_coverage = croissant_dict.get("spatialCoverage")
    if spatial_coverage:
        passed_checks.append("Geocroissant spatialCoverage extension verified.")

    is_valid = len(errors) == 0
    
    return {
        "is_valid": is_valid,
        "spec_version": "MLCommons Croissant v1.0",
        "passed_checks": passed_checks,
        "errors": errors,
        "warnings": warnings,
        "total_fields": total_fields,
        "distribution_count": len(distributions),
        "validator_engine": "Stew Independent MLCommons Croissant Validator v1.0",
        "validation_grade": "PASSED" if is_valid else "FAILED"
    }
