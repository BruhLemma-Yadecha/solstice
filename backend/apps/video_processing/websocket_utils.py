from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import VideoJob


def send_job_update(job_id):
    """Send job status update via WebSocket"""
    channel_layer = get_channel_layer()
    
    try:
        job = VideoJob.objects.select_related("input_video").get(id=job_id)
        job_data = {
            "id": str(job.id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "pose_data_file": f"http://127.0.0.1:8008{job.pose_data_file.url}" if job.pose_data_file else None,
            "input_video": {
                "id": str(job.input_video.id),
                "file": f"http://127.0.0.1:8008{job.input_video.file.url}" if job.input_video and job.input_video.file else "",
            },
        }
        
        # Send to specific job group
        async_to_sync(channel_layer.group_send)(
            f'job_{job_id}',
            {
                'type': 'job_status_update',
                'job_data': job_data
            }
        )
        
        # Send to job list group
        async_to_sync(channel_layer.group_send)(
            'job_list',
            {
                'type': 'job_update',
                'job_data': job_data
            }
        )
        
    except VideoJob.DoesNotExist:
        pass


def send_job_list_update():
    """Send complete job list update via WebSocket"""
    channel_layer = get_channel_layer()
    
    jobs = VideoJob.objects.select_related("input_video").all().order_by("-created_at")
    jobs_data = []
    for job in jobs:
        jobs_data.append({
            "id": str(job.id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "pose_data_file": f"http://127.0.0.1:8008{job.pose_data_file.url}" if job.pose_data_file else None,
            "input_video": {
                "id": str(job.input_video.id),
                "file": f"http://127.0.0.1:8008{job.input_video.file.url}" if job.input_video and job.input_video.file else "",
            },
        })
    
    async_to_sync(channel_layer.group_send)(
        'job_list',
        {
            'type': 'job_list_update',
            'jobs_data': jobs_data
        }
    )


def send_latest_data_update():
    """Send latest data update via WebSocket"""
    channel_layer = get_channel_layer()
    
    try:
        # Get the latest completed job with CSV data
        job = VideoJob.objects.select_related("input_video").filter(
            status='COMPLETED',
            pose_data_file__isnull=False
        ).exclude(pose_data_file__exact='').order_by('-created_at').first()
        
        if not job:
            return
            
        # Safely handle norm_pose_data_file
        norm_csv_url = None
        if job.norm_pose_data_file and hasattr(job.norm_pose_data_file, 'url'):
            try:
                norm_csv_url = f"http://127.0.0.1:8008{job.norm_pose_data_file.url}"
            except ValueError:
                norm_csv_url = None
        
        latest_data = {
            "video1": f"http://127.0.0.1:8008{job.input_video.file.url}",
            "csv_url": f"http://127.0.0.1:8008{job.pose_data_file.url}",
            "norm_csv_url": norm_csv_url,
            "video_id": str(job.input_video.id),
            "job_id": str(job.id)
        }
        
        # Send to latest data group
        async_to_sync(channel_layer.group_send)(
            'latest_data',
            {
                'type': 'latest_data_update',
                'latest_data': latest_data
            }
        )
        
    except Exception as e:
        print(f"Error sending latest data update: {e}")
