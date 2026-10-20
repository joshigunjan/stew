"""
Direct 1-Click Deposition Engine for Zenodo and InvenioRDM (Rodare/TORE).
"""
from clara.depositor.zenodo import create_zenodo_draft_deposition
from clara.depositor.invenio import create_invenio_draft_deposition

__all__ = ["create_zenodo_draft_deposition", "create_invenio_draft_deposition"]
