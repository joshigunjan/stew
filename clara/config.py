import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "data_store"
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

class ClaraConfig(BaseModel):
    # LLM Service (Default: Helmholtz Blablador at JSC)
    blablador_base_url: str = os.getenv(
        "BLABLADOR_BASE_URL",
        "https://api.helmholtz-blablador.fz-juelich.de/v1"
    )
    blablador_api_key: str = os.getenv("BLABLADOR_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    default_model: str = os.getenv("BLABLADOR_MODEL", "alias-fast")
    
    # Local fallback/offline mode if no API key provided
    offline_mode: bool = False
    
    # Server configuration
    host: str = os.getenv("CLARA_HOST", "127.0.0.1")
    port: int = int(os.getenv("CLARA_PORT", "8000"))
    
    # Storage
    storage_dir: Path = STORAGE_DIR

config = ClaraConfig()
