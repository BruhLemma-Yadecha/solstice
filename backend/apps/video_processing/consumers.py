import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import VideoJob


class JobStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.job_id = self.scope['url_route']['kwargs']['job_id']
        self.job_group_name = f'job_{self.job_id}'

        # Join job group
        await self.channel_layer.group_add(
            self.job_group_name,
            self.channel_name
        )

        await self.accept()

        # Send current job status when client connects
        job_data = await self.get_job_status()
        if job_data:
            await self.send(text_data=json.dumps(job_data))

    async def disconnect(self, close_code):
        # Leave job group
        await self.channel_layer.group_discard(
            self.job_group_name,
            self.channel_name
        )

    # Receive message from job group
    async def job_status_update(self, event):
        job_data = event['job_data']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(job_data))

    @database_sync_to_async
    def get_job_status(self):
        try:
            job = VideoJob.objects.select_related("input_video").get(id=self.job_id)
            return {
                "id": str(job.id),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "pose_data_file": f"http://127.0.0.1:8008{job.pose_data_file.url}" if job.pose_data_file else None,
                "input_video": {
                    "id": str(job.input_video.id),
                    "file": f"http://127.0.0.1:8008{job.input_video.file.url}" if job.input_video and job.input_video.file else "",
                },
            }
        except VideoJob.DoesNotExist:
            return None


class JobListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'job_list'

        # Join job list group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send current job list when client connects
        jobs_data = await self.get_all_jobs()
        await self.send(text_data=json.dumps({
            'type': 'job_list',
            'jobs': jobs_data
        }))

    async def disconnect(self, close_code):
        # Leave job list group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from job list group
    async def job_list_update(self, event):
        jobs_data = event['jobs_data']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'job_list',
            'jobs': jobs_data
        }))

    # Receive message for specific job update
    async def job_update(self, event):
        job_data = event['job_data']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'job_update',
            'job': job_data
        }))

    @database_sync_to_async
    def get_all_jobs(self):
        jobs = VideoJob.objects.select_related("input_video").all().order_by("-created_at")
        data = []
        for job in jobs:
            data.append({
                "id": str(job.id),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "pose_data_file": f"http://127.0.0.1:8008{job.pose_data_file.url}" if job.pose_data_file else None,
                "input_video": {
                    "id": str(job.input_video.id),
                    "file": f"http://127.0.0.1:8008{job.input_video.file.url}" if job.input_video and job.input_video.file else "",
                },
            })
        return data


class LatestDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'latest_data'

        # Join latest data group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send current latest data when client connects
        latest_data = await self.get_latest_data()
        if latest_data:
            await self.send(text_data=json.dumps(latest_data))

    async def disconnect(self, close_code):
        # Leave latest data group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from latest data group
    async def latest_data_update(self, event):
        latest_data = event['latest_data']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(latest_data))

    @database_sync_to_async
    def get_latest_data(self):
        try:
            # Get the latest completed job with CSV data
            job = VideoJob.objects.select_related("input_video").filter(
                status='COMPLETED',
                pose_data_file__isnull=False
            ).exclude(pose_data_file__exact='').order_by('-created_at').first()
            
            if not job:
                return None
                
            # Safely handle norm_pose_data_file
            norm_csv_url = None
            if job.norm_pose_data_file and hasattr(job.norm_pose_data_file, 'url'):
                try:
                    norm_csv_url = f"http://127.0.0.1:8008{job.norm_pose_data_file.url}"
                except ValueError:
                    norm_csv_url = None
            
            return {
                "video1": f"http://127.0.0.1:8008{job.input_video.file.url}",
                "csv_url": f"http://127.0.0.1:8008{job.pose_data_file.url}",
                "norm_csv_url": norm_csv_url,
                "video_id": str(job.input_video.id),
                "job_id": str(job.id)
            }
        except Exception:
            return None
