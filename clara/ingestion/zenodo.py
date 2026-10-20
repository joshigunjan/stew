import re
import io
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import httpx

from clara.config import STORAGE_DIR
from clara.profiler.base import DatasetProfile
from clara.profiler.inspector import inspect_dataset

def parse_zenodo_identifier(input_str: str) -> Optional[str]:
    """
    Extracts Zenodo record ID from:
    - URL (https://zenodo.org/records/15008662 or /record/15008662)
    - DOI (10.5281/zenodo.15008662 or https://doi.org/10.5281/zenodo.15008662)
    - Raw ID (15008662)
    """
    cleaned = input_str.strip()
    
    # URL patterns
    m_url = re.search(r'zenodo\.org/records?/(\d+)', cleaned, re.IGNORECASE)
    if m_url:
        return m_url.group(1)
        
    # DOI patterns
    m_doi = re.search(r'10\.5281/zenodo\.(\d+)', cleaned, re.IGNORECASE)
    if m_doi:
        return m_doi.group(1)
        
    # Raw numeric ID
    if cleaned.isdigit():
        return cleaned
        
    return None

def resolve_doi_metadata(doi: str) -> Optional[Dict[str, Any]]:
    """
    Resolves non-Zenodo DOIs via DataCite content negotiation.
    """
    cleaned_doi = re.sub(r'^https?://doi\.org/', '', doi.strip())
    url = f"https://doi.org/{cleaned_doi}"
    headers = {"Accept": "application/vnd.datacite.datacite+json, application/json"}
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None

def fetch_and_profile_zenodo_record(zenodo_input: str) -> Tuple[DatasetProfile, Dict[str, Any]]:
    """
    Given a Zenodo DOI, URL, or record ID:
    1. Queries Zenodo REST API for metadata and files
    2. Downloads the primary tabular/scientific data file
    3. Profiles the data and attaches Zenodo provenance metadata
    """
    record_id = parse_zenodo_identifier(zenodo_input)
    if not record_id:
        raise ValueError(f"Could not parse valid Zenodo Record ID or DOI from: '{zenodo_input}'")

    api_url = f"https://zenodo.org/api/records/{record_id}"
    
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(api_url)
        if resp.status_code != 200:
            raise ValueError(f"Zenodo API returned status {resp.status_code} for record {record_id}")
        record_data = resp.json()

    metadata = record_data.get("metadata", {})
    files = record_data.get("files", [])
    if not files:
        raise ValueError(f"No files found in Zenodo record {record_id}")

    # Prioritize tabular / scientific files
    supported_exts = [".csv", ".tsv", ".parquet", ".geojson", ".json", ".zip"]
    target_file_info = None
    
    for ext in supported_exts:
        for f in files:
            fname = f.get("key", "").lower()
            if fname.endswith(ext):
                target_file_info = f
                break
        if target_file_info:
            break
            
    if not target_file_info:
        # Fall back to first file
        target_file_info = files[0]

    filename = target_file_info.get("key", f"zenodo_{record_id}_data")
    download_url = target_file_info.get("links", {}).get("self")
    if not download_url:
        download_url = target_file_info.get("links", {}).get("content")

    if not download_url:
        raise ValueError(f"Could not determine download link for file: {filename}")

    # Download file
    local_path = STORAGE_DIR / f"zenodo_{record_id}_{filename}"
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        file_resp = client.get(download_url)
        if file_resp.status_code != 200:
            raise ValueError(f"Failed to download file from {download_url} (HTTP {file_resp.status_code})")
            
        # If it's a zip file, inspect its contents and extract first CSV
        if filename.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(file_resp.content)) as z:
                # find CSV or tabular inside zip
                csv_members = [m for m in z.namelist() if m.lower().endswith(('.csv', '.tsv', '.parquet', '.geojson'))]
                if csv_members:
                    extracted_name = csv_members[0]
                    local_path = STORAGE_DIR / f"zenodo_{record_id}_{Path(extracted_name).name}"
                    with open(local_path, "wb") as f_out:
                        f_out.write(z.read(extracted_name))
                else:
                    # just write the zip
                    with open(local_path, "wb") as f_out:
                        f_out.write(file_resp.content)
        else:
            with open(local_path, "wb") as f_out:
                f_out.write(file_resp.content)

    # Deterministic profiling
    profile = inspect_dataset(local_path)
    
    # Enrich with Zenodo metadata
    profile.title = metadata.get("title") or profile.title
    keywords = metadata.get("keywords", [])
    if isinstance(keywords, list):
        profile.domain_field = ", ".join(keywords)
    
    license_info = metadata.get("license", {})
    if isinstance(license_info, dict):
        profile.license = license_info.get("id", "CC-BY-4.0")
    elif isinstance(license_info, str):
        profile.license = license_info

    creators = [c.get("name", "") for c in metadata.get("creators", [])]
    profile.metadata_context = {
        "source": "Zenodo",
        "record_id": record_id,
        "doi": record_data.get("doi") or f"10.5281/zenodo.{record_id}",
        "zenodo_url": f"https://zenodo.org/records/{record_id}",
        "publication_date": metadata.get("publication_date", ""),
        "creators": creators,
        "description": metadata.get("description", "")
    }

    return profile, record_data
