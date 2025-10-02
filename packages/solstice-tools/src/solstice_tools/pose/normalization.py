"""
Pose normalization utilities for standardizing pose data across different people and distances.

This module provides functions to normalize pose landmarks by:
1. Scaling based on shoulder width for size consistency
2. Centering based on hip midpoint for position consistency
"""

import numpy as np
import pandas as pd
from io import StringIO
from typing import List, Optional

from ..exceptions import NormalizationError, InvalidDataError

LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12
LEFT_HIP_IDX = 23
RIGHT_HIP_IDX = 24


def normalize_pose_frame(
    landmarks: np.ndarray, target_shoulder_width: float = 0.25
) -> np.ndarray:
    """
    Normalize a single frame of pose landmarks by centering and scaling.

    This makes poses comparable across different people and distances by:
    1. Scaling based on shoulder width to a target size
    2. Centering based on hip midpoint to frame center

    Args:
        landmarks: 1D numpy array of shape (n_landmarks * 3,) containing [x0, y0, z0, x1, y1, z1, ...]
        target_shoulder_width: Target shoulder width as fraction of frame width (default: 0.25)

    Returns:
        Normalized landmarks as 1D numpy array of same shape

    Raises:
        InvalidDataError: If landmarks array has invalid shape or missing required landmarks
        NormalizationError: If normalization calculation fails
    """
    try:
        # Validate input using the dedicated validation function
        validate_pose_landmarks(landmarks)

        coords = landmarks.reshape(-1, 3)  # n_landmarks, 3) - (x, y, z)

        left_shoulder = coords[LEFT_SHOULDER_IDX]
        right_shoulder = coords[RIGHT_SHOULDER_IDX]

        shoulder_distance = np.linalg.norm(left_shoulder[:2] - right_shoulder[:2])

        # Calculate scale factor (avoid division by zero)
        if shoulder_distance > 0:
            scale_factor = target_shoulder_width / shoulder_distance
        else:
            scale_factor = 1.0  # No scaling if shoulders are at the same point

        # Apply scaling to x,y coordinates only (preserve z)
        coords[:, :2] = coords[:, :2] * scale_factor

        # Centre point using hip midpoint
        left_hip = coords[LEFT_HIP_IDX]
        right_hip = coords[RIGHT_HIP_IDX]
        current_center = (left_hip + right_hip) / 2

        # Target center is (0.5, 0.5) for x,y coordinates (center of frame)
        target_center = np.array([0.5, 0.5, current_center[2]])  # Keep original z
        translation = target_center - current_center
        coords = coords + translation

        # Step 3: Ensure coordinates stay within reasonable bounds [0, 1]
        # Allow some margin outside frame for larger poses
        coords[:, :2] = np.clip(coords[:, :2], -0.3, 1.3)

        return coords.flatten()

    except (IndexError, ValueError) as e:
        raise NormalizationError(f"Failed to normalize pose frame: {e}") from e


def normalize_pose_csv_data(
    csv_bytes: bytes,
    target_shoulder_width: float = 0.25,
    required_landmarks: Optional[List[int]] = None,
) -> bytes:
    """
    Normalize pose data from CSV bytes and return normalized CSV bytes.

    Args:
        csv_bytes: Raw CSV data as bytes
        target_shoulder_width: Target shoulder width for normalization (default: 0.25)
        required_landmarks: Optional list of landmark indices that must be present

    Returns:
        Normalized CSV data as bytes

    Raises:
        InvalidDataError: If CSV data is malformed or missing required columns
        NormalizationError: If normalization fails
    """
    try:
        csv_text = csv_bytes.decode("utf-8")
        df = pd.read_csv(StringIO(csv_text))

        if df.empty:
            raise InvalidDataError("CSV contains no data")

        # Use only landmark columns (more reliable than all coordinate columns)
        landmark_cols = [col for col in df.columns if "landmark_" in col]
        if not landmark_cols:
            raise InvalidDataError("No landmark columns found in CSV")

        coordinate_data = df[landmark_cols].values  # shape: (frames, n_landmarks*3)

        # Validate each frame before normalization
        for i, frame_data in enumerate(coordinate_data):
            try:
                validate_pose_landmarks(frame_data)
            except InvalidDataError as e:
                raise InvalidDataError(
                    f"Invalid pose landmarks in frame {i}: {e}"
                ) from e

        normalized_data = np.apply_along_axis(
            lambda frame: normalize_pose_frame(frame, target_shoulder_width),
            1,
            coordinate_data,
        )

        df_normalized = df.copy()
        df_normalized[landmark_cols] = normalized_data

        output_buffer = StringIO()
        df_normalized.to_csv(output_buffer, index=False)
        return output_buffer.getvalue().encode("utf-8")

    except UnicodeDecodeError as e:
        raise InvalidDataError(f"Invalid CSV encoding: {e}") from e
    except pd.errors.EmptyDataError as e:
        raise InvalidDataError(f"Empty or invalid CSV: {e}") from e
    except (InvalidDataError, NormalizationError):
        raise
    except Exception as e:
        raise NormalizationError(f"Failed to normalize pose CSV: {e}") from e


def validate_pose_landmarks(landmarks: np.ndarray) -> None:
    """
    Validate that pose landmarks array has the expected structure.

    Args:
        landmarks: Landmarks array to validate

    Raises:
        InvalidDataError: If landmarks array is invalid
    """
    try:
        if landmarks.size == 0:
            raise InvalidDataError("Empty landmarks array")

        if landmarks.size % 3 != 0:
            raise InvalidDataError(
                f"Landmarks array size ({landmarks.size}) is not divisible by 3"
            )

        coords = landmarks.reshape(-1, 3)
        n_landmarks = coords.shape[0]

        required_indices = [
            LEFT_SHOULDER_IDX,
            RIGHT_SHOULDER_IDX,
            LEFT_HIP_IDX,
            RIGHT_HIP_IDX,
        ]
        max_required_idx = max(required_indices)
        if n_landmarks <= max_required_idx:
            raise InvalidDataError(
                f"Need at least {max_required_idx + 1} landmarks, got {n_landmarks}"
            )

        if np.any(np.isnan(coords)):
            raise InvalidDataError("Landmarks contain NaN values")

        if np.any(np.isinf(coords)):
            raise InvalidDataError("Landmarks contain infinite values")

    except (ValueError, AttributeError) as e:
        raise InvalidDataError(f"Invalid landmarks array: {e}") from e
