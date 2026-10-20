---
title: Stew - The Helmholtz AI Data Steward
emoji: 🍲
colorFrom: green
colorTo: yellow
sdk: gradio
app_file: app.py
pinned: false
license: apache-2.0
---

# 🍲 Stew: The Helmholtz AI Data Steward
### Sovereign FAIR² & MLCommons Croissant Research Data Management for the Helmholtz Association

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![Croissant](https://img.shields.io/badge/Metadata-MLCommons_Croissant-orange.svg)](https://mlcommons.org/working-groups/data/croissant/)
[![RO-Crate](https://img.shields.io/badge/Packaging-RO--Crate_v1.1-red.svg)](https://www.researchobject.org/ro-crate/)
[![Helmholtz Cloud](https://img.shields.io/badge/LLM-Helmholtz_Blablador_(JSC)-6495ED.svg)](https://helmholtz-blablador.fz-juelich.de/)

**Stew** is an open-source, sovereign, local-first scientific AI Data Steward designed for researchers across the **Helmholtz Association** (and open science communities worldwide). Developed as a sovereign alternative to commercial publisher tools, Stew transforms raw research data into certified, publication-ready, and AI-actionable scientific assets without commercial publisher lock-in or mandatory article processing charges (APCs).

---

## ✨ Key Capabilities

- **🌐 Universal Web & Repository Ingestion**:
  - Ingest directly from **Zenodo DOIs** (e.g., `10.5281/zenodo.15008662`), resolving metadata and primary observation assets via REST API.
  - Ingest from **Open Scientific Web Directories** (e.g., Forschungszentrum Jülich `datapub.fz-juelich.de`), parsing Apache/Nginx directory indices, extracting remote file tables, and integrating repository `README.md` data cards.
  - Direct URL download for remote CSV, Parquet, HDF5, NetCDF, or GeoTIFF files.
  - Local multi-format dropzone.

- **🔬 Broad Scientific Format Support**:
  - **Tabular & Columnar**: CSV, TSV, Parquet.
  - **Hierarchical & Multidimensional**: HDF5 (`.h5`, `.hdf5`, `.he5`), NetCDF (`.nc`, `.netcdf`).
  - **Spreadsheets**: Microsoft Excel (`.xlsx`, `.xls`).
  - **Geospatial**: GeoJSON, GeoTIFF (`.tif`, `.tiff`) with automatic CRS detection and bounding box computation.
  - **Scientific Archives**: ZIP (`.zip`) and TAR (`.tar.gz`).

- **🥐 MLCommons Croissant & Geocroissant**:
  - Generates standard `croissant.jsonld` conforming to the MLCommons specification.
  - Supports multi-file collection distributions and spatial bounding boxes.
  - Datasets are instantly ingestible by **Hugging Face (`load_dataset()`)**, **PyTorch**, **TensorFlow**, and **JAX**.

- **📊 Empirical Schema Profiling & Sentinel Detection**:
  - Deterministically computes null ratios, distinct counts, min/max distributions, and value frequencies.
  - Automatically flags ambiguous sentinel missing codes (e.g., `-999`, `-9999`, `9999`, `NaN`) for researcher confirmation.

- **📈 FAIR² Compliance Index**:
  - Computes an objective 0–100 compliance score structured into four dimensions:
    - **Findable** (Max 25): Persistent identifiers, title, domain classification.
    - **Accessible** (Max 25): Open non-proprietary formats, open science licensing.
    - **Interoperable** (Max 25): QUDT physical units, geospatial coverage, Croissant schemas.
    - **Reusable** (Max 25): Data dictionary completeness, sentinel handling, provenance.
  - Issues AI-Readiness certification grades (`A (AI-Ready)`, `B (FAIR Compliant)`, `C (Needs Curation)`).

- **🤖 Stew AI Steward Chat**:
  - Powered by **Helmholtz Blablador** (hosted at Jülich Supercomputing Centre) via OpenAI-compatible endpoints.
  - Full local deterministic fallback when running offline or without an API token.
  - Includes an interactive **FAIR Stewardship Audit Checklist** to verify physical units, sentinel flags, and acquisition protocols.

- **📖 Standardized Data Dictionaries & Data Articles**:
  - Generates comprehensive variable dictionaries in Markdown and CSV.
  - Synthesizes formal publication-ready FAIR Data Article drafts (Methods, Overview, Validation, Machine Learning Readiness).

- **📦 Sovereign RO-Crate Packaging & Deposit**:
  - Bundles data, Croissant metadata, data dictionaries, and provenance into certified **RO-Crate v1.1** ZIP packages.
  - Direct deposition guidance for Helmholtz repositories: **Rodare (HZDR)**, **TORE (FZJ)**, **Zenodo (CERN)**, and **B2SHARE (EUDAT)**.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/joshigunjan/stew.git
cd stew

# Create virtual environment with uv (recommended) or standard venv
uv venv --python 3.12 .venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .
```

Alternatively using standard pip:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Helmholtz Blablador (Optional)

Stew works out of the box in local deterministic mode. To connect live LLM inference via the Jülich Supercomputing Centre:

```bash
export BLABLADOR_API_KEY="your-helmholtz-access-token"
export BLABLADOR_MODEL="alias-fast"  # alias-fast, alias-code, or llama3-70b-instruct
```

*You can also configure the token directly inside the web UI under **⚙️ LLM Settings**.*

### 3. Launch the Web Cockpit

```bash
python run.py --port 8000 --reload
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## 🏛️ Helmholtz & Open Science Architecture

```
                 +-----------------------------------------------+
                 |              RESEARCH DATA INPUT              |
                 |  Zenodo DOIs  *  FZJ Datapub  *  Local Files  |
                 |   HDF5 / NetCDF / Parquet / CSV / GeoJSON     |
                 +-----------------------+-----------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   STEW INGESTION & PROFILER   |
                         |  Schema * Missing Sentinels   |
                         |  Statistics * Spatial BBox    |
                         +---------------+---------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                         STEW SOVEREIGN STEWARDSHIP CORE                         |
|                                                                                 |
|   +-----------------------+   +-----------------------+   +------------------+  |
|   | FAIR² COMPLIANCE      |   | HELMHOLTZ BLABLADOR   |   | MLCOMMONS        |  |
|   | F:25 A:25 I:25 R:25   |   | JSC LLM Inference     |   | CROISSANT        |  |
|   | AI-Readiness Grade    |   | Local Heuristic Core  |   | Geocroissant     |  |
|   +-----------------------+   +-----------------------+   +------------------+  |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
                 +-----------------------------------------------+
                 |             OUTPUT ARTIFACTS & DEPOSIT        |
                 |  MLCommons Croissant JSON-LD                  |
                 |  Standardized Data Dictionary (MD & CSV)      |
                 |  FAIR Data Article Manuscript                 |
                 |  Certified RO-Crate v1.1 ZIP Package          |
                 |  -> Rodare (HZDR) / TORE (FZJ) / Zenodo       |
                 +-----------------------------------------------+
```

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).
