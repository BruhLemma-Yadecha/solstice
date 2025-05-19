import logging
import os
from .mediapipe import MEDIAPIPE_MODELS, run_mediapipe_on_video

# Get an instance of a logger
logger = logging.getLogger(__name__)


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
        ValueError: If the specified algorithm_id is unknown.
        FileNotFoundError: If the video_file_path does not exist.
        Exception: For any errors during pose estimation processing.
    """
    logger.info(
        f"Generating pose data for video '{video_file_path}' using algorithm ID {algorithm_id}"
    )

    if not os.path.exists(video_file_path):
        logger.error(f"Video file not found at path: {video_file_path}")
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    try:
        if algorithm_id == 1:
            csv_bytes = run_mediapipe_on_video(
                video_file_path, MEDIAPIPE_MODELS.POSE_LANDMARKER_LITE
            )
        elif algorithm_id == 2:
            csv_bytes = run_mediapipe_on_video(
                video_file_path, MEDIAPIPE_MODELS.POSE_LANDMARKER_FULL
            )
        elif algorithm_id == 3:
            csv_bytes = run_mediapipe_on_video(
                video_file_path, MEDIAPIPE_MODELS.POSE_LANDMARKER_HEAVY
            )
        else:
            logger.error(f"Unknown pose estimation algorithm ID: {algorithm_id}")
            raise ValueError(f"Unknown pose estimation algorithm ID: {algorithm_id}")

        logger.info(
            f"Successfully generated pose data CSV for {video_file_path} using algorithm {algorithm_id}"
        )
        return csv_bytes

    except FileNotFoundError:
        raise
    except ValueError:
        raise
    except Exception as e:
        logger.error(
            f"Error during pose estimation for {video_file_path} with algorithm {algorithm_id}: {e}",
            exc_info=True,
        )
        raise Exception(f"Pose estimation failed for algorithm {algorithm_id}: {e}")


# Example of how this might be called from your Celery task:
#
# from .models import VideoJob
# from .services import pose_extraction
#
# def some_celery_task(job_id):
#     job = VideoJob.objects.get(id=job_id)
#     video_path = job.input_video.file.path # Assuming input_video is a ForeignKey to Video model
#     algo_id = job.pose_algorithm_id
#
#     try:
#         csv_data_bytes = pose_extraction.generate_pose_data_csv(video_path, algo_id)
#         # ... then save csv_data_bytes to job.pose_data_file ...
#     except Exception as e:
#         # ... handle error ...
