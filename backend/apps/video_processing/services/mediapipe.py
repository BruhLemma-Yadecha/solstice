import logging
import os
import io
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
from django.conf import settings
from enum import IntEnum


class MEDIAPIPE_MODELS(IntEnum):
    POSE_LANDMARKER_LITE = 1
    POSE_LANDMARKER_FULL = 2
    POSE_LANDMARKER_HEAVY = 3


logger = logging.getLogger(__name__)

PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode
BaseOptions = mp.tasks.BaseOptions
MpImage = mp.Image
MpImageFormat = mp.ImageFormat

# Global cache for landmarker instances to avoid re-initialization in the same worker process
_LANDMARKER_CACHE = {}

if not os.path.isdir(settings.MEDIAPIPE_MODELS_BASE_PATH):
    logger.warning(
        f"The MediaPipe models directory does not exist: {settings.MEDIAPIPE_MODELS_BASE_PATH}. "
        "Please create it and place your .task model files there, or configure MEDIAPIPE_MODELS_BASE_PATH in settings.py."
    )


def _get_landmarker(model_asset_path: str):
    if model_asset_path in _LANDMARKER_CACHE:
        logger.debug(f"Using cached PoseLandmarker for model: {model_asset_path}")
        return _LANDMARKER_CACHE[model_asset_path]

    if not os.path.exists(model_asset_path):
        logger.error(f"MediaPipe model file not found: {model_asset_path}")
        detailed_error_msg = (
            f"MediaPipe model file '{os.path.basename(model_asset_path)}' not found at expected path: {model_asset_path}. "
            f"Ensure the model is present in the '{settings.MEDIAPIPE_MODELS_BASE_PATH}' directory "
            "or that MEDIAPIPE_MODELS_BASE_PATH in Django settings is correctly configured."
        )
        raise FileNotFoundError(detailed_error_msg)

    try:
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_asset_path),
            running_mode=VisionRunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        landmarker = PoseLandmarker.create_from_options(options)
        _LANDMARKER_CACHE[model_asset_path] = landmarker
        logger.info(
            f"Initialized and cached PoseLandmarker for model: {model_asset_path}"
        )
        return landmarker
    except Exception as e:
        logger.error(
            f"Error creating PoseLandmarker for model {model_asset_path}: {e}",
            exc_info=True,
        )
        raise


def run_mediapipe_on_video(video_file_path: str, algorithm_id: int) -> bytes:
    logger.info(
        f"Running MediaPipe pose estimation for video '{video_file_path}' using algorithm ID {algorithm_id}"
    )

    model_mapping = {
        1: "pose_landmarker_lite.task",
        2: "pose_landmarker_full.task",
        3: "pose_landmarker_heavy.task",
    }

    model_file_name = model_mapping.get(algorithm_id)
    if not model_file_name:
        logger.error(f"Unknown MediaPipe algorithm ID: {algorithm_id}")
        raise ValueError(f"Unknown MediaPipe algorithm ID: {algorithm_id}")

    model_asset_path = os.path.join(
        settings.MEDIAPIPE_MODELS_BASE_PATH, model_file_name
    )
    logger.info(
        f"Using MediaPipe model: {model_asset_path} for algorithm ID {algorithm_id}"
    )

    if not os.path.exists(video_file_path):
        logger.error(
            f"Video file for MediaPipe processing not found: {video_file_path}"
        )
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    landmarker_instance = _get_landmarker(model_asset_path)

    cap = cv2.VideoCapture(video_file_path)
    if not cap.isOpened():
        logger.error(f"Error: Could not open video {video_file_path}")
        raise IOError(f"Could not open video {video_file_path}")

    all_pose_positions = []
    frame_number = 0
    logger.debug(f"Starting frame processing for video: {video_file_path}")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = MpImage(image_format=MpImageFormat.SRGB, data=rgb_frame)

            try:
                pose_landmarker_result = landmarker_instance.detect_for_video(
                    mp_image, frame_timestamp_ms
                )
            except Exception as e:
                logger.warning(
                    f"Error during landmark detection on frame {frame_number} of {video_file_path}: {e}"
                )
                frame_number += 1
                continue

            frame_data = {"frame": frame_number, "timestamp_ms": frame_timestamp_ms}
            if pose_landmarker_result.pose_landmarks:
                for person_landmarks in pose_landmarker_result.pose_landmarks:
                    for i, landmark in enumerate(person_landmarks):
                        frame_data[f"landmark_{i}_x"] = landmark.x
                        frame_data[f"landmark_{i}_y"] = landmark.y
                        frame_data[f"landmark_{i}_z"] = landmark.z
            all_pose_positions.append(frame_data)

            if (
                frame_number > 0 and frame_number % 100 == 0
            ):  # Avoid logging frame 0 initially
                logger.debug(
                    f"Processed frame {frame_number} at timestamp {frame_timestamp_ms}ms for {video_file_path}"
                )
            frame_number += 1
    finally:
        cap.release()
        logger.info(
            f"Finished processing video {video_file_path}. Total frames processed: {frame_number - 1 if frame_number > 0 else 0}"
        )

    if not all_pose_positions:
        logger.warning(
            f"No pose positional data was extracted from {video_file_path} using algorithm {algorithm_id}."
        )
        return b"frame,timestamp_ms\n"

    df_pose_positions = pd.DataFrame(all_pose_positions)
    cols_to_front = ["frame", "timestamp_ms"]
    landmark_cols = sorted(
        [col for col in df_pose_positions.columns if col.startswith("landmark_")]
    )
    final_columns = cols_to_front + landmark_cols
    df_pose_positions = df_pose_positions.reindex(columns=final_columns)

    csv_buffer = io.StringIO()
    df_pose_positions.to_csv(csv_buffer, index=False, float_format="%.5f")
    csv_bytes = csv_buffer.getvalue().encode("utf-8")
    logger.info(
        f"MediaPipe processing complete for {video_file_path}, CSV data generated ({len(csv_bytes)} bytes)."
    )
    return csv_bytes
