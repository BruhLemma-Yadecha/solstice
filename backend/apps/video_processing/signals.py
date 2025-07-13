from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.files.storage import default_storage

from .models import Video, VideoJob
from .websocket_utils import send_job_update, send_job_list_update, send_latest_data_update


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


@receiver(post_save, sender=VideoJob)
def job_status_changed(sender, instance, created, **kwargs):
    """
    Send WebSocket update when a VideoJob is created or updated.
    """
    try:
        send_job_update(instance.id)
        if created:
            send_job_list_update()
        
        # Send latest data update if job is completed and has CSV data
        if instance.status == 'COMPLETED' and instance.pose_data_file:
            send_latest_data_update()
            
    except Exception:
        # Don't let WebSocket errors affect the main application
        pass
