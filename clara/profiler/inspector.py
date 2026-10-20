from pathlib import Path
import uuid
import zipfile
import pandas as pd

from clara.profiler.base import DatasetProfile
from clara.profiler.tabular import profile_dataframe
from clara.profiler.spatial import profile_geojson
from clara.profiler.hdf5 import profile_hdf5_file

def inspect_dataset(file_path: Path, dataset_id: str = None) -> DatasetProfile:
    """
    Auto-detects file format and executes deterministic profiling.
    Supports CSV, TSV, Parquet, JSON, GeoJSON, Excel (.xlsx/.xls), HDF5 (.h5/.hdf5), and ZIP archives.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    dataset_id = dataset_id or str(uuid.uuid4())[:8]
    ext = file_path.suffix.lower()
    
    # 1. HDF5 (.h5, .hdf5, .he5)
    if ext in [".h5", ".hdf5", ".he5"]:
        try:
            return profile_hdf5_file(file_path, dataset_id)
        except Exception as e:
            pass

    # 2. GeoJSON
    if ext in [".geojson"]:
        profile = profile_geojson(file_path, dataset_id)
        if profile:
            return profile

    # 3. Excel (.xlsx, .xls)
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
        return profile_dataframe(df, file_path, dataset_id)

    # 4. ZIP Archives (peek inside and inspect primary scientific file)
    if ext == ".zip":
        with zipfile.ZipFile(file_path, 'r') as z:
            names = z.namelist()
            # Look for CSV, Parquet, HDF5, GeoJSON
            candidate = next((n for n in names if n.lower().endswith(('.csv', '.parquet', '.h5', '.hdf5', '.geojson', '.xlsx'))), None)
            if candidate:
                extract_dir = file_path.parent / f"extracted_{file_path.stem}"
                extract_dir.mkdir(exist_ok=True)
                extracted_file = extract_dir / Path(candidate).name
                with open(extracted_file, "wb") as f_out:
                    f_out.write(z.read(candidate))
                return inspect_dataset(extracted_file, dataset_id)

    # 5. Tabular loaders (CSV, TSV, Parquet, JSON)
    if ext in [".csv", ".txt"]:
        sample = open(file_path, "r", encoding="utf-8", errors="ignore").read(4096)
        sep = "\t" if "\t" in sample and sample.count("\t") > sample.count(",") else (";" if sample.count(";") > sample.count(",") else ",")
        df = pd.read_csv(file_path, sep=sep, low_memory=False)
    elif ext == ".tsv":
        df = pd.read_csv(file_path, sep="\t", low_memory=False)
    elif ext in [".parquet", ".pq"]:
        df = pd.read_parquet(file_path)
    elif ext in [".json", ".jsonl"]:
        try:
            df = pd.read_json(file_path, lines=True)
        except Exception:
            df = pd.read_json(file_path)
    else:
        # Default try CSV
        df = pd.read_csv(file_path, low_memory=False)
        
    profile = profile_dataframe(df, file_path, dataset_id)
    return profile
