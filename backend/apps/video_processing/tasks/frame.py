import os
import logging
from celery import shared_task

from ..services.pose_extraction import extract_pose_from_image

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="video_processing.process_frame", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def process_frame(self, frame_path):
    """
    Process a single video frame to extract pose landmarks.
    """
    try:
        fname = os.path.basename(frame_path)
        idx = int(fname.split('_')[-1].split('.')[0])
        landmarks = extract_pose_from_image(frame_path)
        return {'frame': idx, 'landmarks': landmarks}
    except Exception as e:
        logger.error(f"Frame processing failed for {frame_path}: {e}", exc_info=True)
        raise
