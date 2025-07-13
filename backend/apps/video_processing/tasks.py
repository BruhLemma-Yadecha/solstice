# apps/video_processing/tasks.py

import os
import GPUtil  # restore for GPU availability check
import logging
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction
from django.conf import settings

# Models and services
from .models import VideoJob
from .services.pose_extraction import generate_pose_data_csv, NoPoseDataError
from .services.pose_normalization import normalize_pose_csv
from .task_modules.scatter import preprocess_and_scatter

# Get an instance of a logger
logger = logging.getLogger(__name__)

# --- Main Processing Pipeline Tasks ---


@shared_task(bind=True, name="video_processing.video_to_pose_data_task")
def video_to_pose_data_task(self, job_id):
    """
    Celery task to extract pose data from an input video.
    It generates new pose data and then triggers the normalization task.
    """
    task_start_time = timezone.now()
    logger.info(f"Job {job_id}: Pose extraction task started")

    try:
        job = VideoJob.objects.get(id=job_id)

        if not job.input_video:
            logger.error(f"Job {job_id}: Input video not found")
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
            f"Job {job_id}: Starting pose extraction (algorithm: {job.pose_algorithm_id}, hash: {job.input_video.file_hash})"
        )

        # Always generate new pose data, deduplication is removed for simplicity.
        logger.info(f"Job {job_id}: Generating new pose data")
        try:
            pose_data_csv_content = generate_pose_data_csv(
                job.input_video.file.path,
                job.pose_algorithm_id,
            )
        except NoPoseDataError as e:
            logger.error(f"Job {job_id}: No pose data extracted: {e}")
            with transaction.atomic():
                job_update = VideoJob.objects.select_for_update().get(id=job_id)
                job_update.status = VideoJob.JobStatus.FAILED
                job_update.error_message = str(e)
                job_update.save()
            return
        # Let other PoseExtractionError bubble to outer handler

        if pose_data_csv_content:
            file_name_base = f"{job.id}_posedata_v{job.pose_algorithm_id}.csv"

            with transaction.atomic():
                job_update = VideoJob.objects.select_for_update().get(id=job_id)
                job_update.pose_data_file.save(
                    file_name_base, ContentFile(pose_data_csv_content), save=False
                )
                job_update.status = VideoJob.JobStatus.POSE_DATA_GENERATED
                job_update.save()  # This save will also commit the file
                # Defer triggering the next task until after the transaction commits
                transaction.on_commit(lambda: normalize_pose_data_task.delay(job_id))
            job.refresh_from_db()

        task_duration = timezone.now() - task_start_time
        logger.info(
            f"Job {job_id}: Task completed in {task_duration.total_seconds():.1f}s (generated pose data)"
        )
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


@shared_task(bind=True, name="video_processing.video_to_pose_data_task_gpu")
def video_to_pose_data_task_gpu(self, job_id):
    logger.info(f"Job {job_id}: Dispatched to GPU queue")
    video_to_pose_data_task(job_id)


# --- Scatter-Gather CPU Workflow ---


@shared_task(bind=True, name="video_processing.video_to_pose_data_task_cpu")
def video_to_pose_data_task_cpu(self, job_id):
    task_start_time = timezone.now()
    logger.info(f"Job {job_id}: CPU scatter-gather task started")

    try:
        result = preprocess_and_scatter.delay(job_id)
        result.get()  # Wait for the scatter task to complete

        task_duration = timezone.now() - task_start_time
        logger.info(
            f"Job {job_id}: CPU scatter-gather task completed in {task_duration.total_seconds():.1f}s"
        )
        return result
    except Exception as e:
        task_duration = timezone.now() - task_start_time
        logger.error(
            f"Job {job_id}: CPU scatter-gather task failed after {task_duration.total_seconds():.1f}s: {e}"
        )
        raise


@shared_task(bind=True, name="video_processing.pose_data_to_armature_video_task")
def pose_data_to_armature_video_task(self, job_id):
    """
    Celery task to generate the final armature video from pose data CSV.
    """
    task_start_time = timezone.now()
    logger.info(f"Job {job_id}: Armature video task started")

    try:
        job = VideoJob.objects.get(id=job_id)  # Fetch job at the beginning

        if (
            not job.norm_pose_data_file or not job.norm_pose_data_file.name
        ):  # Updated field name
            logger.error(
                f"Job {job_id}: Intermediate normalized pose data CSV not found."
            )
            with transaction.atomic():
                job_update = VideoJob.objects.select_for_update().get(id=job_id)
                job_update.status = VideoJob.JobStatus.FAILED
                job_update.error_message = "Intermediate normalized pose data CSV missing for armature video generation."
                job_update.save()
            return

        with transaction.atomic():
            job_update = VideoJob.objects.select_for_update().get(id=job_id)
            job_update.celery_armature_task_id = self.request.id
            job_update.status = VideoJob.JobStatus.GENERATING_ARMATURE_VIDEO
            job_update.save()
        job.refresh_from_db()

        logger.info(f"Job {job_id}: Generating armature video from pose data")

        # output_video_file_path = armature_video_service.generate_video_from_pose_data(
        #     job.norm_pose_data_file.path, # Updated field name
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
            # Save output video file via FileField
            from django.core.files.base import ContentFile

            with open(output_video_file_path, "rb") as f:
                job_complete.output_video_file.save(
                    os.path.basename(output_video_file_path),
                    ContentFile(f.read()),
                    save=False,
                )  # Updated field name
                job_complete.status = VideoJob.JobStatus.COMPLETED
                job_complete.save()  # This save will also commit the file
            job.refresh_from_db()  # Refresh to get the saved file name

        task_duration = timezone.now() - task_start_time
        logger.info(
            f"Job {job_id}: Armature video generation task completed in {task_duration.total_seconds():.1f}s"
        )
    except VideoJob.DoesNotExist:
        logger.error(f"VideoJob with id {job_id} not found for armature video task.")
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


@shared_task(bind=True, name="video_processing.normalize_pose_data_task")
def normalize_pose_data_task(self, job_id):
    """
    Celery task to normalize pose landmark CSV data by anatomical method (shoulder-scale + hip-center).
    """
    start = timezone.now()
    logger.info(f"Job {job_id}: Starting pose data normalization")
    try:
        # Load job and mark status
        job = VideoJob.objects.get(id=job_id)
        with transaction.atomic():
            uj = VideoJob.objects.select_for_update().get(id=job_id)
            uj.status = VideoJob.JobStatus.NORMALISING_POSE_DATA
            uj.save()

        # Read original CSV bytes
        with job.pose_data_file.open("rb") as f:
            csv_bytes = f.read()
        # Normalize via service
        norm_bytes = normalize_pose_csv(csv_bytes)

        # Save normalized CSV
        fname = f"{job.id}_normposedata_v{job.pose_algorithm_id}.csv"
        with transaction.atomic():
            uj = VideoJob.objects.select_for_update().get(id=job_id)
            uj.norm_pose_data_file.save(fname, ContentFile(norm_bytes), save=False)
            uj.status = VideoJob.JobStatus.POSE_DATA_NORMALISED
            uj.save()

        elapsed = (timezone.now() - start).total_seconds()
        logger.info(f"Job {job_id}: Normalization done in {elapsed:.1f}s")
        # Defer triggering the next task until after the transaction commits
        transaction.on_commit(lambda: pose_data_to_armature_video_task.delay(job_id))
    except VideoJob.DoesNotExist:
        logger.error(f"VideoJob {job_id} not found for normalization.")
    except Exception as e:
        logger.error(f"Normalize task error for job {job_id}: {e}", exc_info=True)
        with transaction.atomic():
            uj = VideoJob.objects.select_for_update().get(id=job_id)
            uj.status = VideoJob.JobStatus.FAILED
            uj.error_message = f"Normalization error: {e}"
            uj.save()


def is_gpu_available():
    """Check if at least one GPU is available for processing."""
    return len(GPUtil.getAvailable()) > 0


def dispatch_pose_extraction_task(job_id):
    """
    Dispatches the pose extraction task to GPU or CPU queue based on availability.
    """
    if is_gpu_available():
        logger.info(f"Dispatching job {job_id} to GPU queue.")
        video_to_pose_data_task_gpu.delay(job_id)
    else:
        logger.info(f"Dispatching job {job_id} to CPU queue.")
        video_to_pose_data_task_cpu.delay(job_id)
