from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage

from .models import Video, VideoJob


@receiver(post_delete, sender=Video)
def delete_video_file(sender, instance, **kwargs):
    """
    Deletes the video file from storage when the Video object is deleted.
    """
    if instance.file and instance.file.name:
        try:
            default_storage.delete(instance.file.name)
        except Exception:
            pass


@receiver(post_delete, sender=VideoJob)
def delete_job_files(sender, instance, **kwargs):
    """
    Deletes associated pose data CSV and output video file when the VideoJob is deleted.
    """
    # Pose data file
    if instance.pose_data_file and instance.pose_data_file.name:
        try:
            default_storage.delete(instance.pose_data_file.name)
        except Exception:
            pass
    # Output video file
    if getattr(instance, "output_video_file", None) and instance.output_video_file.name:
        try:
            default_storage.delete(instance.output_video_file.name)
        except Exception:
            pass
