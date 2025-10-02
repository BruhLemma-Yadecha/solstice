"""Solstice Tools - Core utilities for video processing and pose analysis."""

__version__ = "0.1.0"

from .pose.normalization import (
    normalize_pose_frame,
    normalize_pose_csv_data,
    validate_pose_landmarks,
)
from .exceptions import (
    SolsticeError,
    PoseProcessingError,
    NormalizationError,
    InvalidDataError,
)

__all__ = [
    "normalize_pose_frame",
    "normalize_pose_csv_data",
    "validate_pose_landmarks",
    "SolsticeError",
    "PoseProcessingError",
    "NormalizationError",
    "InvalidDataError",
]
