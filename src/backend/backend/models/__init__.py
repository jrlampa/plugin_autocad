"""Models package - exports all models from backend.models module and sync models

NOTE: This file uses importlib to load the sibling models.py file because Python's
import system resolves 'backend.models' to this package directory, not the models.py file.
This is a workaround for a naming conflict. Consider refactoring by either:
1. Moving all models from models.py into this package structure, or
2. Renaming the models.py file to something like api_models.py
"""

# Import from the sibling models.py file  
# Since Python resolves 'backend.models' to this package, we import models.py using importlib
import importlib.util
import os

_current_dir = os.path.dirname(__file__)
_models_py_path = os.path.abspath(os.path.join(_current_dir, '..', 'models.py'))

# Load models.py as a standalone module
_spec = importlib.util.spec_from_file_location("_backend_models_module", _models_py_path)
_models_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_models_module)

# Re-export all model classes
# TODO: Consider using dynamic export with getattr/dir to reduce maintenance burden
FrozenBaseModel = _models_module.FrozenBaseModel
HealthResponse = _models_module.HealthResponse
ComponentHealth = _models_module.ComponentHealth
DeepHealthResponse = _models_module.DeepHealthResponse
ProjectUpdateRequest = _models_module.ProjectUpdateRequest
PrepareOsmRequest = _models_module.PrepareOsmRequest
PrepareGeoJsonRequest = _models_module.PrepareGeoJsonRequest
PrepareJobRequest = _models_module.PrepareJobRequest
CadFeature = _models_module.CadFeature
PrepareResponse = _models_module.PrepareResponse
JobStatusResponse = _models_module.JobStatusResponse
ElevationQueryRequest = _models_module.ElevationQueryRequest
ElevationProfileRequest = _models_module.ElevationProfileRequest
ElevationPointResponse = _models_module.ElevationPointResponse
ElevationProfileResponse = _models_module.ElevationProfileResponse
WebhookRegistrationRequest = _models_module.WebhookRegistrationRequest
InternalEvent = _models_module.InternalEvent

# Also export sync models from this package
from backend.models.sync_event import SyncEvent, SyncChangeset, SyncConflict, SyncResult

__all__ = [
    "FrozenBaseModel",
    "HealthResponse",
    "ComponentHealth",
    "DeepHealthResponse",
    "ProjectUpdateRequest",
    "PrepareOsmRequest",
    "PrepareGeoJsonRequest",
    "PrepareJobRequest",
    "CadFeature",
    "PrepareResponse",
    "JobStatusResponse",
    "ElevationQueryRequest",
    "ElevationProfileRequest",
    "ElevationPointResponse",
    "ElevationProfileResponse",
    "WebhookRegistrationRequest",
    "InternalEvent",
    "SyncEvent",
    "SyncChangeset",
    "SyncConflict",
    "SyncResult",
]
