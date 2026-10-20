import io
import os
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from clara.config import config, BASE_DIR, STORAGE_DIR
from clara.profiler.base import DatasetProfile
from clara.profiler.inspector import inspect_dataset
from clara.ingestion.zenodo import fetch_and_profile_zenodo_record
from clara.ingestion.universal_url import ingest_any_url
from clara.steward.agent import StewAgent
from clara.steward.fair_evaluator import evaluate_fair_score
from clara.generators.croissant import generate_croissant_metadata
from clara.generators.dictionary import (
    generate_data_dictionary_records,
    generate_data_dictionary_markdown,
    generate_data_dictionary_csv
)
from clara.generators.ro_crate import generate_ro_crate_metadata
from clara.validators.croissant import validate_croissant_jsonld
from clara.validators.rocrate import validate_rocrate_json
from clara.depositor.zenodo import create_zenodo_draft_deposition
from clara.depositor.invenio import create_invenio_draft_deposition

app = FastAPI(
    title="Stew: The Helmholtz Data Steward",
    description="Sovereign AI Data Steward for FAIR research datasets",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active sessions
DATASET_STORE: Dict[str, DatasetProfile] = {}
CHAT_STORE: Dict[str, List[Dict[str, str]]] = {}
ARTICLE_STORE: Dict[str, str] = {}

steward_agent = StewAgent()

# Web assets directories
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
STATIC_DIR = WEB_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class ChatRequest(BaseModel):
    dataset_id: str
    message: str
    history: List[Dict[str, str]] = []

class SettingsRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

class UniversalImportRequest(BaseModel):
    identifier: Optional[str] = None
    url: Optional[str] = None

ZenodoImportRequest = UniversalImportRequest

class ColumnConfirmationRequest(BaseModel):
    dataset_id: str
    column_name: str
    suggested_unit: Optional[str] = None
    suggested_description: Optional[str] = None
    user_notes: Optional[str] = None

class DepositionRequest(BaseModel):
    dataset_id: str
    target_repository: str = "zenodo"
    access_token: str
    use_sandbox: bool = True

@app.get("/", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
async def serve_index():
    index_file = WEB_DIR / "templates" / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Stew: The Helmholtz Data Steward Running</h1>")

@app.get("/api/status")
async def get_status():
    provider_name = getattr(steward_agent.client, "provider", "Helmholtz Blablador (JSC)")
    return {
        "blablador_base_url": getattr(steward_agent.client, "base_url", config.blablador_base_url),
        "model": getattr(steward_agent.client, "model", config.default_model),
        "is_configured": steward_agent.client.is_configured,
        "provider": provider_name,
        "service": provider_name if steward_agent.client.is_configured else f"{provider_name} (Unconnected - Local Grounded Mode)"
    }

@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    if req.api_key is not None:
        config.blablador_api_key = req.api_key.strip()
    if req.model is not None:
        config.default_model = req.model.strip()
    if req.base_url is not None:
        config.blablador_base_url = req.base_url.strip()
        
    from clara.steward.llm_client import BlabladorClient
    steward_agent.client = BlabladorClient(
        api_key=config.blablador_api_key,
        base_url=config.blablador_base_url,
        model=config.default_model
    )
    return {
        "status": "updated",
        "is_configured": steward_agent.client.is_configured,
        "model": getattr(steward_agent.client, "model", config.default_model),
        "provider": getattr(steward_agent.client, "provider", "Helmholtz Blablador (JSC)")
    }

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_dataset"
    save_path = STORAGE_DIR / filename
    
    with open(save_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    profile = inspect_dataset(save_path)
    review = steward_agent.conduct_initial_review(profile)
    fair = evaluate_fair_score(profile)
    
    DATASET_STORE[profile.dataset_id] = profile
    CHAT_STORE[profile.dataset_id] = [
        {"role": "assistant", "content": review}
    ]
    
    return {
        "dataset_id": profile.dataset_id,
        "profile": profile.model_dump(),
        "initial_review": review,
        "fair_score": fair
    }

@app.post("/api/import-url")
@app.post("/api/import-zenodo")
async def import_url_endpoint(req: UniversalImportRequest):
    target = req.url or req.identifier or ""
    if not target:
        raise HTTPException(status_code=400, detail="Missing URL or identifier")
    try:
        profile, record_data = ingest_any_url(target)
        review = steward_agent.conduct_initial_review(profile)
        fair = evaluate_fair_score(profile)
        
        DATASET_STORE[profile.dataset_id] = profile
        CHAT_STORE[profile.dataset_id] = [
            {"role": "assistant", "content": review}
        ]
        
        return {
            "dataset_id": profile.dataset_id,
            "profile": profile.model_dump(),
            "initial_review": review,
            "fair_score": fair,
            "record_metadata": record_data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/load-sample/{sample_name}")
async def load_sample(sample_name: str):
    sample_file = BASE_DIR / "examples" / sample_name
    if not sample_file.exists():
        raise HTTPException(status_code=404, detail="Sample dataset not found")
        
    profile = inspect_dataset(sample_file)
    review = steward_agent.conduct_initial_review(profile)
    fair = evaluate_fair_score(profile)
    
    DATASET_STORE[profile.dataset_id] = profile
    CHAT_STORE[profile.dataset_id] = [
        {"role": "assistant", "content": review}
    ]
    
    return {
        "dataset_id": profile.dataset_id,
        "profile": profile.model_dump(),
        "initial_review": review,
        "fair_score": fair
    }

@app.get("/api/profile/{dataset_id}")
async def get_profile(dataset_id: str):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[dataset_id]
    fair = evaluate_fair_score(profile)
    return {
        "profile": profile.model_dump(),
        "fair": fair
    }

@app.post("/api/chat")
async def chat_with_steward(req: ChatRequest):
    if req.dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    profile = DATASET_STORE[req.dataset_id]
    history = req.history or CHAT_STORE.get(req.dataset_id, [])
    
    reply = steward_agent.chat_turn(profile, history, req.message)
    
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    CHAT_STORE[req.dataset_id] = history
    
    return {
        "reply": reply,
        "history": history
    }

@app.get("/api/croissant/{dataset_id}")
async def get_croissant(dataset_id: str):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[dataset_id]
    croissant_data = generate_croissant_metadata(profile)
    validation = validate_croissant_jsonld(croissant_data)
    return {
        "metadata": croissant_data,
        "validation": validation
    }

@app.get("/api/dictionary/{dataset_id}")
async def get_dictionary(dataset_id: str):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[dataset_id]
    return {
        "records": generate_data_dictionary_records(profile),
        "markdown": generate_data_dictionary_markdown(profile),
        "csv": generate_data_dictionary_csv(profile)
    }

@app.post("/api/column/confirm")
async def confirm_column(req: ColumnConfirmationRequest):
    if req.dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[req.dataset_id]
    if req.column_name not in profile.columns:
        raise HTTPException(status_code=404, detail=f"Column '{req.column_name}' not found")
        
    col = profile.columns[req.column_name]
    if req.suggested_unit is not None:
        col.suggested_unit = req.suggested_unit.strip()
    if req.suggested_description is not None:
        col.suggested_description = req.suggested_description.strip()
    col.user_confirmed = True
    col.provenance_type = "USER_VERIFIED"
    col.confidence_score = 1.0
    col.provenance_evidence = f"Researcher confirmed and approved: {req.user_notes or 'Direct approval'}"
    
    return {
        "status": "confirmed",
        "column": col.model_dump()
    }

@app.get("/api/domain-audit/{dataset_id}")
async def get_domain_audit(dataset_id: str):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[dataset_id]
    return profile.domain_standards or {}

@app.post("/api/deposit")
async def deposit_endpoint(req: DepositionRequest):
    if req.dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not req.access_token or len(req.access_token.strip()) < 5:
        raise HTTPException(status_code=400, detail="Personal Access Token is required for repository deposition.")
        
    profile = DATASET_STORE[req.dataset_id]
    croissant_doc = generate_croissant_metadata(profile)
    crate_doc = generate_ro_crate_metadata(profile)
    dict_md = generate_data_dictionary_markdown(profile)
    
    import json
    files_bundle = {
        "croissant.jsonld": json.dumps(croissant_doc, indent=2),
        "ro-crate-metadata.json": json.dumps(crate_doc, indent=2),
        "data_dictionary.md": dict_md
    }
    
    try:
        if req.target_repository.lower() == "zenodo":
            result = create_zenodo_draft_deposition(
                profile,
                access_token=req.access_token,
                use_sandbox=req.use_sandbox,
                files_to_upload=files_bundle
            )
        else:
            result = create_invenio_draft_deposition(
                profile,
                access_token=req.access_token,
                repository=req.target_repository.lower()
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/article/{dataset_id}")
async def get_article(dataset_id: str, notes: Optional[str] = Form("")):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[dataset_id]
    article_md = steward_agent.draft_data_article(profile, user_notes=notes or "")
    ARTICLE_STORE[dataset_id] = article_md
    return {"article_markdown": article_md}

@app.get("/api/ro-crate/{dataset_id}")
async def get_ro_crate(dataset_id: str):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = DATASET_STORE[dataset_id]
    crate_data = generate_ro_crate_metadata(profile)
    validation = validate_rocrate_json(crate_data)
    return {
        "metadata": crate_data,
        "validation": validation
    }

@app.get("/api/export/{dataset_id}")
async def export_fair_package(dataset_id: str):
    if dataset_id not in DATASET_STORE:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    profile = DATASET_STORE[dataset_id]
    croissant_data = generate_croissant_metadata(profile)
    ro_crate_data = generate_ro_crate_metadata(profile)
    dict_csv = generate_data_dictionary_csv(profile)
    dict_md = generate_data_dictionary_markdown(profile)
    article_md = ARTICLE_STORE.get(dataset_id) or steward_agent.draft_data_article(profile)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # Add original data file if exists
        data_file_path = STORAGE_DIR / profile.file_name
        if not data_file_path.exists():
            data_file_path = BASE_DIR / "examples" / profile.file_name
        if data_file_path.exists():
            z.write(data_file_path, arcname=profile.file_name)
            
        z.writestr("croissant.jsonld", generate_croissant_json(croissant_data))
        z.writestr("ro-crate-metadata.json", generate_croissant_json(ro_crate_data))
        z.writestr("data_dictionary.csv", dict_csv)
        z.writestr("data_dictionary.md", dict_md)
        z.writestr("fair_data_article.md", article_md)
        z.writestr("README.md", f"# {profile.title}\n\nExported via Stew Helmholtz AI Data Steward.\n\n{dict_md}")

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=fair_package_{dataset_id}.zip"}
    )

def generate_croissant_json(data: dict) -> str:
    import json
    return json.dumps(data, indent=2)
