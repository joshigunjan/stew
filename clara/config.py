import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "data_store"
STORAGE_DIR.mkdir(exist_ok=True, parents=True)

# Optional .env loading for local development and embedded deployments
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

class ClaraConfig(BaseModel):
    # LLM Service (Default: Helmholtz Blablador at JSC)
    blablador_base_url: str = os.getenv(
        "BLABLADOR_BASE_URL",
        "https://api.helmholtz-blablador.fz-juelich.de/v1"
    )
    blablador_api_key: str = os.getenv("BLABLADOR_API_KEY", os.getenv("OPENAI_API_KEY", os.getenv("HF_TOKEN", "")))
    default_model: str = os.getenv("BLABLADOR_MODEL", "alias-fast")
    
    # Local fallback/offline mode if no API key provided
    offline_mode: bool = False
    
    # Server configuration
    host: str = os.getenv("CLARA_HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", os.getenv("CLARA_PORT", "8000")))
    
    # Storage
    storage_dir: Path = STORAGE_DIR

config = ClaraConfig()
