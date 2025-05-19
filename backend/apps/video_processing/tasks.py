# apps/video_processing/tasks.py

import os
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from django.conf import settings  # Added for settings.MEDIA_ROOT

from .models import VideoJob, Video
# Import your service functions here once they are created
from .services import pose_extraction

# Get an instance of a logger
logger = logging.getLogger(__name__)

# --- Main Processing Pipeline Tasks ---


@shared_task(bind=True, name="video_processing.video_to_pose_data_task")
def video_to_pose_data_task(self, job_id):
    """
    Celery task to extract pose data from an input video.
    It checks for existing pose data from a previous identical job (same video hash & pose algorithm id).
    If found, it reuses the data; otherwise, it generates new pose data.
    Then, it triggers the armature video generation task.
    """
    try:
        # It's good practice to fetch the job within a transaction if you plan to update it.
        # However, the main updates happen after potential I/O.
        # For status updates during the process, select_for_update might be too broad.
        # We'll use atomic transactions for specific save operations.
        job = VideoJob.objects.get(id=job_id)

        if not job.input_video:
            logger.error(f"Job {job_id}: Input video not found.")
            with transaction.atomic():
                job_update = VideoJob.objects.select_for_update().get(id=job_id)
                job_update.status = VideoJob.JobStatus.FAILED
                job_update.error_message = "Input video not associated with the job."
                job_update.save()
            return

        with transaction.atomic():
            job_update = VideoJob.objects.select_for_update().get(id=job_id)
            job_update.celery_pose_task_id = self.request.id
            job_update.status = VideoJob.JobStatus.EXTRACTING_POSE
            job_update.save()

        job.refresh_from_db()

        logger.info(
            f"Starting pose extraction for job {job_id}, algorithm ID {job.pose_algorithm_id}, input video hash: {job.input_video.file_hash}"
        )

        # Deduplication logic
        existing_pose_data_source_job = (
            VideoJob.objects.filter(
                input_video__file_hash=job.input_video.file_hash,
                pose_algorithm_id=job.pose_algorithm_id,  # Updated field name
                status__in=[
                    VideoJob.JobStatus.POSE_DATA_GENERATED,
                    VideoJob.JobStatus.ARMATURE_VIDEO_QUEUED,
                    VideoJob.JobStatus.GENERATING_ARMATURE_VIDEO,
                    VideoJob.JobStatus.COMPLETED,
                ],
                pose_data_file__isnull=False,  # Updated field name
            )
            .exclude(id=job.id)
            .exclude(pose_data_file__exact="")
            .order_by("-created_at")
            .first()
        )

        pose_data_csv_content = None
        reused_pose_data = False

        if (
            existing_pose_data_source_job
            and existing_pose_data_source_job.pose_data_file.name
        ):  # Updated field name
            try:
                logger.info(
                    f"Job {job_id}: Found existing pose data from job {existing_pose_data_source_job.id}. Reusing."
                )
                existing_pose_data_source_job.pose_data_file.open(
                    "rb"
                )  # Updated field name
                pose_data_csv_content = (
                    existing_pose_data_source_job.pose_data_file.read()
                )  # Updated field name
                existing_pose_data_source_job.pose_data_file.close()  # Updated field name
                reused_pose_data = True
            except Exception as e:
                logger.warning(
                    f"Job {job_id}: Failed to read existing pose data from {existing_pose_data_source_job.id}. Will regenerate. Error: {e}"
                )
                pose_data_csv_content = None
                reused_pose_data = False

        if not pose_data_csv_content:
            logger.info(
                f"Job {job_id}: No reusable pose data found or failed to read. Generating new pose data."
            )
            pose_data_csv_content = pose_extraction.generate_pose_data_csv(job.input_video.file.path, job.pose_algorithm_id)
            reused_pose_data = False

        if pose_data_csv_content:
            file_name_base = (
                f"{job.id}_posedata_v{job.pose_algorithm_id}.csv"
            )

            with transaction.atomic():
                job_update = VideoJob.objects.select_for_update().get(id=job_id)
                job_update.pose_data_file.save(
                    file_name_base, ContentFile(pose_data_csv_content), save=False
                )  # Updated field name
                job_update.status = VideoJob.JobStatus.POSE_DATA_GENERATED
                job_update.save()  # This save will also commit the file
            job.refresh_from_db()  # Refresh to get the saved file name
            logger.info(
                f"Job {job_id}: Pose data CSV {'reused and ' if reused_pose_data else ''}saved as {job.pose_data_file.name}"
            )  # Updated field name
        else:
            raise ValueError("Pose data CSV content is empty or generation failed.")

        # logger.info(
        #     f"Job {job_id}: Pose data generation successful. Triggering armature video task."
        # )
        # pose_data_to_armature_video_task.si(job_id).apply_async()

    except VideoJob.DoesNotExist:
        logger.error(f"VideoJob with id {job_id} not found for pose extraction.")
    except Exception as e:
        logger.error(
            f"Error in video_to_pose_data_task for job {job_id}: {e}", exc_info=True
        )
        try:
            with transaction.atomic():
                job_fail = VideoJob.objects.select_for_update().get(id=job_id)
                job_fail.status = VideoJob.JobStatus.FAILED
                job_fail.error_message = f"Pose extraction failed: {str(e)}"
                job_fail.save()
        except VideoJob.DoesNotExist:
            logger.error(
                f"VideoJob {job_id} not found when trying to mark as FAILED after error."
            )


@shared_task(bind=True, name="video_processing.pose_data_to_armature_video_task")
def pose_data_to_armature_video_task(self, job_id):
    """
    Celery task to generate the final armature video from pose data CSV.
    """
    try:
        job = VideoJob.objects.get(id=job_id)  # Fetch job at the beginning

        if not job.pose_data_file or not job.pose_data_file.name:  # Updated field name
            logger.error(f"Job {job_id}: Intermediate pose data CSV not found.")
            with transaction.atomic():
                job_update = VideoJob.objects.select_for_update().get(id=job_id)
                job_update.status = VideoJob.JobStatus.FAILED
                job_update.error_message = (
                    "Intermediate pose data CSV missing for armature video generation."
                )
                job_update.save()
            return

        with transaction.atomic():
            job_update = VideoJob.objects.select_for_update().get(id=job_id)
            job_update.celery_armature_task_id = self.request.id
            job_update.status = VideoJob.JobStatus.GENERATING_ARMATURE_VIDEO
            job_update.save()
        job.refresh_from_db()

        logger.info(
            f"Starting armature video generation for job {job_id} from {job.pose_data_file.path}"
        )  # Updated field name

        # output_video_file_path = armature_video_service.generate_video_from_pose_data(
        #     job.pose_data_file.path, # Updated field name
        #     job.input_video.file.path if job.input_video else None
        # )

        mock_output_dir = os.path.join(settings.MEDIA_ROOT, "output_videos")
        os.makedirs(mock_output_dir, exist_ok=True)
        output_video_file_path = os.path.join(
            mock_output_dir, f"{job.id}_armature_output.mp4"
        )
        with open(output_video_file_path, "w") as f:
            f.write("This is a mock armature video.")
        logger.info(
            f"Job {job_id}: Mock output video created at {output_video_file_path}"
        )

        with transaction.atomic():
            job_complete = VideoJob.objects.select_for_update().get(id=job_id)
            job_complete.output_video_path = output_video_file_path
            job_complete.output_generated_at = timezone.now()
            job_complete.status = VideoJob.JobStatus.COMPLETED
            job_complete.save()

        logger.info(
            f"Job {job_id}: Armature video generation successful. Output at: {output_video_file_path}"
        )

    except VideoJob.DoesNotExist:
        logger.error(
            f"VideoJob with id {job_id} not found for armature video generation."
        )
    except Exception as e:
        logger.error(
            f"Error in pose_data_to_armature_video_task for job {job_id}: {e}",
            exc_info=True,
        )
        try:
            with transaction.atomic():
                job_fail = VideoJob.objects.select_for_update().get(id=job_id)
                job_fail.status = VideoJob.JobStatus.FAILED
                job_fail.error_message = f"Armature video generation failed: {str(e)}"
                job_fail.save()
        except VideoJob.DoesNotExist:
            logger.error(
                f"VideoJob {job_id} not found when trying to mark as FAILED after error."
            )

