import json
from typing import Dict, Any, Optional
import httpx

from clara.profiler.base import DatasetProfile

ZENODO_PROD_URL = "https://zenodo.org/api/deposit/depositions"
ZENODO_SANDBOX_URL = "https://sandbox.zenodo.org/api/deposit/depositions"

def create_zenodo_draft_deposition(
    profile: DatasetProfile,
    access_token: str,
    use_sandbox: bool = True,
    files_to_upload: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Creates a new draft deposition in Zenodo (or Zenodo Sandbox),
    reserving a persistent DOI and uploading certified metadata artifacts.
    """
    base_endpoint = ZENODO_SANDBOX_URL if use_sandbox else ZENODO_PROD_URL
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json"
    }
    
    # Metadata payload following Zenodo Deposit API schema
    metadata = {
        "title": profile.title,
        "upload_type": "dataset",
        "description": f"<p>{profile.title} curated via Stew (Helmholtz AI Data Steward). Includes MLCommons Croissant metadata, standardized Data Dictionary, and RO-Crate v1.1 package.</p>",
        "creators": [
            {"name": "Helmholtz Open Science Community", "affiliation": "Helmholtz Association"}
        ],
        "access_right": "open",
        "license": "CC-BY-4.0",
        "keywords": [
            "FAIR data",
            "MLCommons Croissant",
            "RO-Crate",
            "Helmholtz Association",
            profile.domain_field or "Open Science"
        ]
    }
    
    payload = {"metadata": metadata}
    
    with httpx.Client(timeout=30.0) as client:
        # Step 1: Create Draft Deposition
        response = client.post(base_endpoint, headers=headers, json=payload)
        if response.status_code not in [200, 201]:
            try:
                err_data = response.json()
                msg = err_data.get("message") or str(err_data)
            except Exception:
                msg = response.text
            raise RuntimeError(f"Zenodo API error ({response.status_code}): {msg}")
            
        deposition_data = response.json()
        dep_id = deposition_data.get("id")
        bucket_url = deposition_data.get("links", {}).get("bucket")
        html_url = deposition_data.get("links", {}).get("html")
        reserved_doi = deposition_data.get("metadata", {}).get("prereserve_doi", {}).get("doi")
        
        # Step 2: Upload Metadata Artifacts if provided
        uploaded_files = []
        if bucket_url and files_to_upload:
            file_headers = {"Authorization": f"Bearer {access_token.strip()}"}
            for fname, content_str in files_to_upload.items():
                content_bytes = content_str.encode("utf-8")
                file_upload_url = f"{bucket_url}/{fname}"
                f_resp = client.put(file_upload_url, headers=file_headers, content=content_bytes)
                if f_resp.status_code in [200, 201]:
                    uploaded_files.append(fname)
                    
        return {
            "status": "success",
            "deposition_id": dep_id,
            "reserved_doi": reserved_doi or f"10.5281/zenodo.{dep_id}",
            "deposit_url": html_url or f"https://{'sandbox.' if use_sandbox else ''}zenodo.org/deposit/{dep_id}",
            "environment": "Zenodo Sandbox" if use_sandbox else "Zenodo Production",
            "files_uploaded": uploaded_files,
            "message": f"Successfully created draft deposition with reserved DOI: {reserved_doi or dep_id}"
        }
