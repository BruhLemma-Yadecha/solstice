import os
import csv
import shutil
import logging
from celery import shared_task
from django.db import transaction
from django.core.files.base import ContentFile

from ..models import VideoJob

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="video_processing.aggregate_results")
def aggregate_results(self, results, job_id, workdir):
    """
    Reduce phase: combine per-frame landmarks into CSV, save to VideoJob, and clean up.
    """
    try:
        if not results:
            raise ValueError("No results to aggregate")

        sorted_res = sorted(results, key=lambda r: r["frame"])
        csv_path = os.path.join(workdir, f"{job_id}_pose_results.csv")

        with open(csv_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)

            # Check if we have landmarks to determine header
            if sorted_res and sorted_res[0]["landmarks"]:
                header = ["frame"] + [
                    f"landmark_{i // 3}_{['x', 'y', 'z'][i % 3]}"
                    for i in range(len(sorted_res[0]["landmarks"]))
                ]
            else:
                header = ["frame"]  # Minimal header if no landmarks

            writer.writerow(header)

            for res in sorted_res:
                row = [res["frame"]] + res["landmarks"]
                writer.writerow(row)

        with transaction.atomic():
            job_update = VideoJob.objects.select_for_update().get(id=job_id)
            with open(csv_path, "rb") as f:
                job_update.pose_data_file.save(
                    os.path.basename(csv_path), ContentFile(f.read()), save=False
                )
            job_update.status = VideoJob.JobStatus.POSE_DATA_GENERATED
            job_update.save()

        # Trigger normalization after pose data is saved
        from ..tasks import normalize_pose_data_task
        transaction.on_commit(lambda: normalize_pose_data_task.delay(job_id))

        shutil.rmtree(workdir)
        return csv_path
    except Exception as e:
        logger.error(f"Aggregation failed for job {job_id}: {e}", exc_info=True)
        try:
            with transaction.atomic():
                jf = VideoJob.objects.select_for_update().get(id=job_id)
                jf.status = VideoJob.JobStatus.FAILED
                jf.error_message = f"Aggregation error: {e}"
                jf.save()
        except VideoJob.DoesNotExist:
            logger.error(f"VideoJob {job_id} missing when marking aggregation failure.")
        finally:
            if os.path.isdir(workdir):
                shutil.rmtree(workdir, ignore_errors=True)
        raise
