"""Offline carrier recognition and optional FedEx lookup."""

from .fedex_tracker import (
    FedexConfigurationError,
    FedexLookupError,
    FedexTracker,
    default_ops_meta,
    normalize_fedex_track_ops_meta,
)
from .recognition import CarrierCandidate, RecognitionResult, recognize_tracking_number
from .unified_tracker import UnifiedTracker

__all__ = [
    "CarrierCandidate",
    "RecognitionResult",
    "recognize_tracking_number",
    "UnifiedTracker",
    "FedexTracker",
    "FedexConfigurationError",
    "FedexLookupError",
    "default_ops_meta",
    "normalize_fedex_track_ops_meta",
]
