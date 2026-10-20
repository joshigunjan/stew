from pathlib import Path
from typing import Dict, Any, List
import h5py

from clara.profiler.base import ColumnProfile, DatasetProfile

def profile_hdf5_file(file_path: Path, dataset_id: str) -> DatasetProfile:
    """
    Profiles an HDF5 scientific dataset (.h5, .hdf5), extracting datasets,
    dimensions, shapes, dtypes, attributes (units, scale), and compression.
    """
    file_path = Path(file_path)
    columns_profile: Dict[str, ColumnProfile] = {}
    preview_records: List[Dict[str, Any]] = []
    summary_notes: List[str] = []
    
    with h5py.File(file_path, "r") as f:
        datasets_found = []
        
        def visitor(name, node):
            if isinstance(node, h5py.Dataset):
                datasets_found.append((name, node))

        f.visititems(visitor)
        
        summary_notes.append(f"HDF5 Archive containing {len(datasets_found)} internal datasets/arrays.")
        
        for name, dset in datasets_found:
            shape_str = str(dset.shape)
            dtype_str = str(dset.dtype)
            
            # Attributes
            attrs = {k: str(v) for k, v in dset.attrs.items()}
            unit = attrs.get("units") or attrs.get("unit") or ""
            desc = attrs.get("long_name") or attrs.get("description") or f"Array dataset: {name}"
            
            # Sample values if small or 1D/2D
            samples = []
            min_val = None
            max_val = None
            try:
                if dset.size > 0 and dset.size <= 10000:
                    data_slice = dset[...]
                    min_val = float(data_slice.min())
                    max_val = float(data_slice.max())
                    samples = [str(x) for x in data_slice.flatten()[:5]]
                elif dset.size > 10000:
                    # Take small slice from corner
                    slice_idx = tuple(slice(0, min(2, dim)) for dim in dset.shape)
                    samples = [f"Shape: {shape_str}"]
            except Exception:
                pass

            col_prof = ColumnProfile(
                name=name,
                inferred_type="multidimensional_array" if len(dset.shape) > 1 else "numeric",
                physical_dtype=f"{dtype_str} {shape_str}",
                total_count=dset.size,
                null_count=0,
                null_ratio=0.0,
                distinct_count=dset.shape[0] if len(dset.shape) > 0 else 1,
                is_unique=False,
                sample_values=samples,
                min_val=min_val,
                max_val=max_val,
                suggested_semantic_type="scientific_raster" if len(dset.shape) >= 2 else "measurement",
                suggested_unit=unit,
                suggested_description=f"{desc} (Dimensions: {shape_str})",
                missing_value_markers=[]
            )
            columns_profile[name] = col_prof
            
            preview_records.append({
                "dataset_path": name,
                "shape": shape_str,
                "dtype": dtype_str,
                "size_elements": f"{dset.size:,}",
                "chunks": str(dset.chunks) if dset.chunks else "contiguous",
                "compression": str(dset.compression),
                "attributes": str(attrs) if attrs else "-"
            })

    return DatasetProfile(
        dataset_id=dataset_id,
        title=file_path.stem.replace("_", " ").title(),
        file_name=file_path.name,
        file_format="hdf5",
        file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
        row_count=len(columns_profile),
        column_count=len(columns_profile),
        columns=columns_profile,
        preview_rows=preview_records,
        summary_notes=summary_notes,
        is_spatial=any("geo" in k.lower() or "lat" in k.lower() for k in columns_profile.keys()),
        metadata_context={"format": "HDF5", "datasets_count": len(columns_profile)}
    )
