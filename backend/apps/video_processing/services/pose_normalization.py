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
    Normalize a single frame of pose data by centering the person in the frame
    and scaling to a consistent size based on shoulder width.
    This makes poses comparable across different people and distances.

    Args:
        frame: 1D numpy array of length (n_landmarks*3).
    Returns:
        1D numpy array of same shape with normalized coords centered and scaled.
    """
    # Reshape into (n_landmarks, 3) - (x, y, z)
    coords = frame.reshape(-1, 3)
    
    # Step 1: Calculate scale factor based on shoulder width
    left_shoulder = coords[LEFT_SHOULDER_IDX]
    right_shoulder = coords[RIGHT_SHOULDER_IDX]
    shoulder_distance = np.linalg.norm(left_shoulder[:2] - right_shoulder[:2])  # Only x,y for distance
    
    # Target shoulder width (normalized size)
    target_shoulder_width = 0.25  # About 1/4 of frame width
    
    # Calculate scale factor (avoid division by zero)
    if shoulder_distance > 0:
        scale_factor = target_shoulder_width / shoulder_distance
    else:
        scale_factor = 1.0
    
    # Apply scaling to x,y coordinates only
    coords[:, :2] = coords[:, :2] * scale_factor
    
    # Step 2: Calculate the center point using hip midpoint (after scaling)
    left_hip = coords[LEFT_HIP_IDX]
    right_hip = coords[RIGHT_HIP_IDX]
    current_center = (left_hip + right_hip) / 2
    
    # Target center is (0.5, 0.5) for x,y coordinates (center of frame)
    target_center = np.array([0.5, 0.5, current_center[2]])  # Keep original z
    
    # Calculate translation needed
    translation = target_center - current_center
    
    # Apply translation to all landmarks
    coords = coords + translation
    
    # Ensure coordinates stay within reasonable bounds [0, 1]
    # Allow some margin outside frame for larger poses
    coords[:, :2] = np.clip(coords[:, :2], -0.3, 1.3)
    
    return coords.flatten()


def normalize_pose_csv(
    csv_bytes: bytes, required_indices: Optional[List[int]] = None
) -> bytes:
    """
    Read CSV bytes of pose data, apply per-frame normalization, and return CSV bytes.

    Args:
        csv_bytes: Raw CSV data as bytes.
        required_indices: Optional list of landmark indices required; defaults to shoulders/hips.
    Returns:
        bytes: Normalized CSV data.
    """
    # Load into DataFrame
    text = csv_bytes.decode("utf-8")
    df = pd.read_csv(StringIO(text))
    # Only numeric columns, excluding the 'frame' column
    numeric = df.select_dtypes(include=["number"]).columns
    # Exclude 'frame' column if it exists
    coordinate_columns = [col for col in numeric if col != 'frame']
    data = df[coordinate_columns].to_numpy()  # shape: (frames, n_landmarks*3)
    # Normalize each frame
    normalized = np.apply_along_axis(normalize_pose_frame, 1, data)
    # Build DataFrame
    df_norm = df.copy()
    df_norm[coordinate_columns] = normalized
    # Output
    out_buffer = StringIO()
    df_norm.to_csv(out_buffer, index=False)
    return out_buffer.getvalue().encode("utf-8")
