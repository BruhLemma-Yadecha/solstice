import numpy as np
import pandas as pd
from io import StringIO
from typing import List, Optional

# MediaPipe Pose landmark indices for shoulders and hips
LEFT_SHOULDER_IDX = 11
RIGHT_SHOULDER_IDX = 12
LEFT_HIP_IDX = 23
RIGHT_HIP_IDX = 24


def normalize_pose_frame(frame: np.ndarray) -> np.ndarray:
    """
    Normalize a single frame of pose data (flattened x,y,z coords) by:
     1. Scaling by shoulder distance (unit shoulder width).
     2. Translating so hip midpoint is at origin.

    Args:
        frame: 1D numpy array of length (n_landmarks*3).
    Returns:
        1D numpy array of same shape with normalized coords.
    """
    # Reshape into (n_landmarks, 3)
    coords = frame.reshape(-1, 3)
    # Compute scale (shoulder distance)
    left_sh = coords[LEFT_SHOULDER_IDX]
    right_sh = coords[RIGHT_SHOULDER_IDX]
    scale = np.linalg.norm(left_sh - right_sh)
    if scale == 0:
        scale = 1.0
    coords = coords / scale
    # Center at hip midpoint
    left_hip = coords[LEFT_HIP_IDX]
    right_hip = coords[RIGHT_HIP_IDX]
    center = (left_hip + right_hip) / 2
    coords = coords - center
    return coords.flatten()


def normalize_pose_csv(csv_bytes: bytes, required_indices: Optional[List[int]] = None) -> bytes:
    """
    Read CSV bytes of pose data, apply per-frame normalization, and return CSV bytes.

    Args:
        csv_bytes: Raw CSV data as bytes.
        required_indices: Optional list of landmark indices required; defaults to shoulders/hips.
    Returns:
        bytes: Normalized CSV data.
    """
    # Load into DataFrame
    text = csv_bytes.decode('utf-8')
    df = pd.read_csv(StringIO(text))
    # Only numeric columns
    numeric = df.select_dtypes(include=['number']).columns
    data = df[numeric].to_numpy()  # shape: (frames, n_landmarks*3)
    # Normalize each frame
    normalized = np.apply_along_axis(normalize_pose_frame, 1, data)
    # Build DataFrame
    df_norm = df.copy()
    df_norm[numeric] = normalized
    # Output
    out_buffer = StringIO()
    df_norm.to_csv(out_buffer, index=False)
    return out_buffer.getvalue().encode('utf-8')
