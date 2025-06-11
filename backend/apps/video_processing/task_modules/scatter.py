import os
import tempfile
import shutil
import subprocess
from celery import chord
from django.db import transaction
from django.core.files.base import ContentFile
from celery import shared_task
import logging

from .frame import process_frame
from .aggregate import aggregate_results
from ..models import VideoJob

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="video_processing.preprocess_and_scatter")
def preprocess_and_scatter(self, job_id):
    """
    Scatter phase: extract all frames to a shared directory and trigger processing chord.
    """
    logger.info(f"[SCATTER] preprocess_and_scatter START for job {job_id}")
    workdir = None
    try:
        job = VideoJob.objects.get(id=job_id)
        logger.info(f"[SCATTER] VideoJob loaded: {job}")
        # mark job as extracting
        with transaction.atomic():
            ju = VideoJob.objects.select_for_update().get(id=job_id)
            ju.celery_pose_task_id = self.request.id
            ju.status = VideoJob.JobStatus.EXTRACTING_POSE
            ju.save()
            logger.info(f"[SCATTER] Job status set to EXTRACTING_POSE for job {job_id}")
        # create temp dir and extract frames
        workdir = tempfile.mkdtemp(prefix=f"job_{job_id}_frames_")
        logger.info(f"[SCATTER] Temp workdir created: {workdir}")
        cmd = [
            "ffmpeg",
            "-i",
            job.input_video.file.path,
            "-vsync",
            "0",
            os.path.join(workdir, "frame_%08d.png"),
        ]
        logger.info(f"[SCATTER] Running ffmpeg command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"[SCATTER] ffmpeg completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"[SCATTER] ffmpeg failed with return code {e.returncode}")
            logger.error(f"[SCATTER] ffmpeg stderr: {e.stderr}")
            logger.error(f"[SCATTER] ffmpeg stdout: {e.stdout}")
            raise

        logger.info(f"[SCATTER] ffmpeg finished, listing frames in {workdir}")
        frames = sorted(
            os.path.join(workdir, fn)
            for fn in os.listdir(workdir)
            if fn.endswith(".png")
        )
        logger.info(f"[SCATTER] Found {len(frames)} frames for job {job_id}")

        if not frames:
            raise ValueError(f"No frames extracted from video for job {job_id}")

        # Log sample frame names for debugging
        sample_frames = frames[:3] + (frames[-3:] if len(frames) > 3 else [])
        logger.info(
            f"[SCATTER] Sample frame names: {[os.path.basename(f) for f in sample_frames]}"
        )

        chord_result = chord(
            (process_frame.s(path) for path in frames),
            aggregate_results.s(job_id, workdir),
        ).apply_async()
        logger.info(
            f"[SCATTER] Chord dispatched for job {job_id} with {len(frames)} frames"
        )
        return frames
    except Exception as e:
        logger.error(f"Job {job_id}: Scatter phase failed: {e}", exc_info=True)
        # mark job as failed
        try:
            with transaction.atomic():
                jf = VideoJob.objects.select_for_update().get(id=job_id)
                jf.status = VideoJob.JobStatus.FAILED
                jf.error_message = f"Scatter error: {e}"
                jf.save()
        except VideoJob.DoesNotExist:
            logger.error(f"VideoJob {job_id} missing when marking scatter failure.")
        # cleanup
        if workdir and os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)
        raise
