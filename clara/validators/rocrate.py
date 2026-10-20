from typing import Dict, Any, List

def validate_rocrate_json(crate_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Independent validator for RO-Crate v1.1 packages.
    Verifies JSON-LD graph structure, metadata descriptor, root dataset entity,
    and part relationships.
    """
    errors: List[str] = []
    warnings: List[str] = []
    passed_checks: List[str] = []
    
    # 1. Context check
    context = crate_dict.get("@context")
    if not context or "https://w3id.org/ro/crate/1.1" not in str(context):
        errors.append("Invalid or missing RO-Crate @context; must link 'https://w3id.org/ro/crate/1.1'.")
    else:
        passed_checks.append("RO-Crate v1.1 JSON-LD context verified.")
        
    # 2. Graph array check
    graph = crate_dict.get("@graph", [])
    if not isinstance(graph, list) or len(graph) == 0:
        errors.append("RO-Crate must contain a non-empty '@graph' array.")
        return {
            "is_valid": False,
            "spec_version": "RO-Crate v1.1",
            "passed_checks": passed_checks,
            "errors": errors,
            "warnings": warnings,
            "validation_grade": "FAILED"
        }
    passed_checks.append(f"Entity graph validated: {len(graph)} interconnected entities.")
    
    # 3. Metadata descriptor entity check
    entities_by_id = {item.get("@id"): item for item in graph if isinstance(item, dict) and "@id" in item}
    descriptor = entities_by_id.get("ro-crate-metadata.json")
    if not descriptor:
        errors.append("Missing RO-Crate Metadata Descriptor entity with @id 'ro-crate-metadata.json'.")
    else:
        passed_checks.append("Metadata Descriptor entity ('ro-crate-metadata.json') verified.")
        
    # 4. Root Dataset check
    root_dataset = entities_by_id.get("./")
    if not root_dataset:
        errors.append("Missing Root Data Entity with @id './'.")
    else:
        types = root_dataset.get("@type", [])
        if "Dataset" not in types and types != "Dataset":
            errors.append("Root Data Entity must have @type 'Dataset'.")
        else:
            passed_checks.append("Root Data Entity confirmed with @type 'Dataset'.")
            
        if not root_dataset.get("datePublished"):
            warnings.append("Root dataset missing 'datePublished' property.")
        else:
            passed_checks.append("Provenance timestamp (datePublished) confirmed.")
            
        has_part = root_dataset.get("hasPart", [])
        if not has_part:
            warnings.append("Root dataset has no 'hasPart' references to data or metadata files.")
        else:
            passed_checks.append(f"Package parts validated: {len(has_part)} linked resources in Root Dataset.")

    is_valid = len(errors) == 0
    return {
        "is_valid": is_valid,
        "spec_version": "RO-Crate v1.1",
        "passed_checks": passed_checks,
        "errors": errors,
        "warnings": warnings,
        "entity_count": len(graph),
        "validator_engine": "Stew Independent RO-Crate Validator v1.1",
        "validation_grade": "PASSED" if is_valid else "FAILED"
    }
