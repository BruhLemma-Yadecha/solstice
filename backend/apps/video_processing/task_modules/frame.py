import os
import logging
from celery import shared_task

from ..services.pose_extraction import extract_pose_from_image

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="video_processing.process_frame",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_frame(self, frame_path):
    """
    Process a single video frame to extract pose landmarks.
    """
    try:
        fname = os.path.basename(frame_path)
        logger.info(f"Processing frame: {fname}")

        # Extract frame index from filename like "frame_00000001.png"
        try:
            idx = int(fname.split("_")[-1].split(".")[0])
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse frame index from filename {fname}: {e}")
            raise ValueError(f"Invalid frame filename format: {fname}")

        landmarks = extract_pose_from_image(frame_path)
        logger.info(f"Extracted {len(landmarks)} landmarks from frame {idx}")
        return {"frame": idx, "landmarks": landmarks}
    except Exception as e:
        logger.error(f"Frame processing failed for {frame_path}: {e}", exc_info=True)
        raise
