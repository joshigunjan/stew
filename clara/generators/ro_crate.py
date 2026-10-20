import datetime
from typing import Dict, Any
from clara.profiler.base import DatasetProfile

def generate_ro_crate_metadata(profile: DatasetProfile) -> Dict[str, Any]:
    """
    Generates RO-Crate metadata (ro-crate-metadata.json) compliant with RO-Crate v1.1.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"}
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": profile.title,
            "description": f"Dataset {profile.file_name} curated via Stew Helmholtz AI Data Steward.",
            "datePublished": now_iso,
            "license": {"@id": f"https://spdx.org/licenses/{profile.license}.html"},
            "hasPart": [
                {"@id": profile.file_name},
                {"@id": "croissant.jsonld"},
                {"@id": "data_dictionary.csv"}
            ]
        },
        {
            "@id": profile.file_name,
            "@type": "File",
            "name": profile.file_name,
            "contentSize": profile.file_size_bytes,
            "encodingFormat": f"text/{profile.file_format}" if profile.file_format in ["csv", "tsv"] else "application/octet-stream"
        },
        {
            "@id": "croissant.jsonld",
            "@type": "File",
            "name": "MLCommons Croissant Metadata",
            "encodingFormat": "application/ld+json",
            "conformsTo": {"@id": "http://mlcommons.org/croissant/1.0"}
        },
        {
            "@id": "data_dictionary.csv",
            "@type": "File",
            "name": "Dataset Variable Dictionary",
            "encodingFormat": "text/csv"
        }
    ]

    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": graph
    }
