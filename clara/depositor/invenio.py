from typing import Dict, Any, Optional
import httpx
from clara.profiler.base import DatasetProfile

RODARE_URL = "https://rodare.hzdr.de/api/records"
TORE_URL = "https://tore.fz-juelich.de/api/records"

def create_invenio_draft_deposition(
    profile: DatasetProfile,
    access_token: str,
    repository: str = "rodare",  # rodare or tore
    custom_host: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a draft deposition on Helmholtz InvenioRDM instances
    (Rodare at HZDR or TORE at FZJ).
    """
    if custom_host:
        endpoint = f"{custom_host.rstrip('/')}/api/records"
    elif repository.lower() == "tore":
        endpoint = TORE_URL
    else:
        endpoint = RODARE_URL
        
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json"
    }
    
    # InvenioRDM standard draft payload
    payload = {
        "access": {
            "record": "public",
            "files": "public"
        },
        "files": {
            "enabled": True
        },
        "metadata": {
            "title": profile.title,
            "resource_type": {"id": "dataset"},
            "publication_date": profile.created_at[:10] if profile.created_at else "2026-10-20",
            "creators": [
                {
                    "person_or_org": {
                        "type": "organizational",
                        "name": "Helmholtz Open Science Community"
                    }
                }
            ],
            "description": f"<p>{profile.title} curated via Stew (Helmholtz AI Data Steward). Includes MLCommons Croissant metadata, Data Dictionary, and RO-Crate package.</p>",
            "rights": [{"id": "cc-by-4.0"}]
        }
    }
    
    with httpx.Client(timeout=30.0) as client:
        response = client.post(endpoint, headers=headers, json=payload)
        if response.status_code not in [200, 201]:
            try:
                err_data = response.json()
                msg = err_data.get("message") or str(err_data)
            except Exception:
                msg = response.text
            raise RuntimeError(f"InvenioRDM ({repository}) API error ({response.status_code}): {msg}")
            
        data = response.json()
        record_id = data.get("id")
        links = data.get("links", {})
        html_url = links.get("self_html") or f"{endpoint.replace('/api/records', '')}/records/{record_id}"
        
        return {
            "status": "success",
            "repository": "Rodare (HZDR)" if repository == "rodare" else "TORE (FZJ)",
            "record_id": record_id,
            "deposit_url": html_url,
            "message": f"Successfully created draft record {record_id} on {repository.upper()}"
        }
