import logging
import os
from enum import Enum
from .mediapipe import MEDIAPIPE_MODELS, run_mediapipe_on_video

# Get an instance of a logger
logger = logging.getLogger(__name__)


class PoseAlgorithm(Enum):
    LITE = 1
    FULL = 2
    HEAVY = 3


class PoseExtractionError(Exception):
    """Base exception for pose extraction errors."""


class UnknownAlgorithmError(PoseExtractionError):
    """Raised when the specified algorithm ID is unknown."""


class NoPoseDataError(PoseExtractionError):
    """Raised when no pose data could be extracted from the video."""


def _resolve_algorithm(algorithm_id: int) -> PoseAlgorithm:
    try:
        return PoseAlgorithm(algorithm_id)
    except ValueError as e:
        logger.error(f"Unknown pose estimation algorithm ID: {algorithm_id}")
        raise UnknownAlgorithmError(
            f"Unknown pose estimation algorithm ID: {algorithm_id}"
        ) from e


def generate_pose_data_csv(video_file_path: str, algorithm_id: int) -> bytes:
    """
    Processes the video file using the specified pose estimation algorithm
    and returns the pose data as CSV content (bytes).

    Args:
        video_file_path: Absolute path to the input video file.
        algorithm_id: Integer identifier for the pose estimation algorithm to use.

    Returns:
        bytes: The content of the generated CSV file as bytes.

    Raises:
        UnknownAlgorithmError: If the specified algorithm_id is unknown.
        FileNotFoundError: If the video_file_path does not exist.
        NoPoseDataError: If the video produced no pose data.
        PoseExtractionError: For any other errors during pose estimation processing.
    """
    logger.info(
        f"Generating pose data for video '{video_file_path}' using algorithm ID {algorithm_id}"
    )

    if not os.path.exists(video_file_path):
        logger.error(f"Video file not found at path: {video_file_path}")
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    try:
        algorithm = _resolve_algorithm(algorithm_id)
        model_map = {
            PoseAlgorithm.LITE: MEDIAPIPE_MODELS.POSE_LANDMARKER_LITE,
            PoseAlgorithm.FULL: MEDIAPIPE_MODELS.POSE_LANDMARKER_FULL,
            PoseAlgorithm.HEAVY: MEDIAPIPE_MODELS.POSE_LANDMARKER_HEAVY,
        }
        selected_model = model_map[algorithm]

        csv_bytes = run_mediapipe_on_video(video_file_path, selected_model)

        if not csv_bytes or csv_bytes.strip() == b"":
            logger.warning(f"No pose data extracted from video {video_file_path}")
            raise NoPoseDataError(
                f"No pose data extracted from video: {video_file_path}"
            )

        logger.info(
            f"Successfully generated pose data CSV for {video_file_path} using algorithm {algorithm_id}"
        )
        return csv_bytes

    except FileNotFoundError:
        raise
    except PoseExtractionError:
        raise
    except Exception as e:
        logger.error(
            f"Error during pose estimation for {video_file_path} with algorithm {algorithm_id}: {e}",
            exc_info=True,
        )
        raise PoseExtractionError(
            f"Pose estimation failed for algorithm {algorithm_id}: {e}"
        ) from e
