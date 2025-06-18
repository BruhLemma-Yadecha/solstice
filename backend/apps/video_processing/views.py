# apps/video_processing/views.py

import logging
import hashlib
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Video, VideoJob
from .serializers import (
    VideoSerializer,
    VideoJobCreateSerializer,
    VideoJobDetailSerializer,
)
from .services.utilities import delete_csv, delete_norm_csv

from .tasks import video_to_pose_data_task, dispatch_pose_extraction_task

logger = logging.getLogger(__name__)


class VideoUploadAPIView(APIView):
    """
    API View for uploading videos and creating processing jobs.
    Accepts POST requests with 'video_file' and 'pose_algorithm_id'.
    """

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        """
        Handles POST request to upload a video and start a processing job.
        """
        job_create_serializer = VideoJobCreateSerializer(data=request.data)
        if not job_create_serializer.is_valid():
            logger.warning(
                f"Video upload failed validation: {job_create_serializer.errors}"
            )
            return Response(
                job_create_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = job_create_serializer.validated_data
        uploaded_file = validated_data["video_file"]
        pose_algorithm_id = validated_data["pose_algorithm_id"]

        # 1. Calculate hash of the uploaded file
        hasher = hashlib.sha256()
        uploaded_file.seek(0)  # Ensure reading from the beginning
        for chunk in uploaded_file.chunks():  # Use chunks for potentially large files
            hasher.update(chunk)
        file_hash = hasher.hexdigest()
        uploaded_file.seek(0)  # Reset file pointer for subsequent use

        video_instance = None
        video_created_in_this_request = False

        # 2. Try to find an existing video by hash
        try:
            video_instance = Video.objects.get(file_hash=file_hash)
            logger.info(
                f"Video with hash {file_hash} already exists (ID: {video_instance.id}). Reusing."
            )
        except Video.DoesNotExist:
            # 3. If not found, create a new Video instance
            # The VideoSerializer will handle passing the file to the Video model's save() method,
            # which in turn handles the actual file saving with a unique name and its own hash calculation.
            video_data_for_serializer = {"file": uploaded_file}
            video_serializer = VideoSerializer(
                data=video_data_for_serializer
            )  # Pass the actual file object
            if video_serializer.is_valid():
                try:
                    # The model's save() will calculate its own hash. We've pre-calculated
                    # one for lookup, but the model's hash is the source of truth for the DB record.
                    video_instance = video_serializer.save()  # This will save the file

                    # Sanity check: the hash calculated by the model should match our pre-calculated hash.
                    if video_instance.file_hash != file_hash:
                        logger.error(
                            f"Hash mismatch for new video {video_instance.id}. "
                            f"Pre-calculated: {file_hash}, Model saved with: {video_instance.file_hash}. "
                            "This could indicate an issue in hash calculation consistency or file handling."
                        )
                        # Depending on policy, you might raise an error or proceed with the model's hash.
                        # For now, we'll trust the model's saved hash.

                    video_created_in_this_request = True
                    logger.info(
                        f"New Video instance created: {video_instance.id} with hash {video_instance.file_hash}"
                    )
                except IntegrityError:
                    # This would be an unexpected IntegrityError if the pre-check by hash failed to find it,
                    # but then the model's save() resulted in a hash collision.
                    # This implies a race condition or an issue with the pre-check.
                    # For robustness, try to fetch again.
                    try:
                        video_instance = Video.objects.get(
                            file_hash=file_hash
                        )  # Or video_instance.file_hash if populated
                        logger.warning(
                            f"Recovered from unexpected IntegrityError; video with hash {file_hash} found (ID: {video_instance.id}). Reusing."
                        )
                    except Video.DoesNotExist:
                        logger.error(
                            f"Unexpected IntegrityError during Video save for hash {file_hash}, but video still not found.",
                            exc_info=True,
                        )
                        return Response(
                            {
                                "detail": "Error saving video file due to unexpected conflict."
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                except Exception as e:  # Catch any other error during Video.save()
                    logger.error(
                        f"Error saving new Video instance after hash check: {e}",
                        exc_info=True,
                    )
                    return Response(
                        {"detail": f"Error saving video file: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:  # video_serializer is not valid
                logger.error(
                    f"VideoSerializer errors after hash check: {video_serializer.errors}"
                )
                return Response(
                    video_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

        if not video_instance:
            logger.critical(
                "Video instance is None after processing video file. This indicates a critical logic error in deduplication or creation."
            )
            return Response(
                {"detail": "Internal server error: Could not obtain video reference."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Now create the VideoJob
        try:
            with transaction.atomic():
                video_job = VideoJob.objects.create(
                    input_video=video_instance,
                    pose_algorithm_id=pose_algorithm_id,
                    status=VideoJob.JobStatus.UPLOADED,
                )
                logger.info(
                    f"VideoJob created: {video_job.id} for Video {video_instance.id}"
                )

                # Dispatch pose extraction task to appropriate queue (GPU or CPU)
                dispatch_pose_extraction_task(video_job.id)
                logger.info(f"Pose extraction task dispatched for job {video_job.id}")

            job_detail_serializer = VideoJobDetailSerializer(
                video_job, context={"request": request}
            )
            return Response(job_detail_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                f"Error creating VideoJob or dispatching task for video {video_instance.id}: {e}",
                exc_info=True,
            )
            return Response(
                {"detail": "Error initiating video processing job."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobStatusAPIView(APIView):
    """
    API View to retrieve the status and details of a specific VideoJob.
    Accepts GET requests with a job_id (UUID) in the URL.
    """

    def get(self, request, job_id, *args, **kwargs):
        """
        Handles GET request to fetch job status.
        """
        try:
            job = VideoJob.objects.get(id=job_id)
        except VideoJob.DoesNotExist:
            logger.warning(f"Job status query for non-existent job_id: {job_id}")
            return Response(
                {"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            logger.warning(f"Job status query with invalid UUID format: {job_id}")
            return Response(
                {"detail": "Invalid job ID format."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = VideoJobDetailSerializer(job, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class LatestVideoAndCSVAPIView(APIView):
    """
    API View to get the latest processed video and its pose CSV,
    or for a specific job if job_id is provided as a query param.
    """

    def get(self, request, *args, **kwargs):
        job_id = request.query_params.get("job_id")
        if job_id:
            try:
                job = VideoJob.objects.get(id=job_id)
            except VideoJob.DoesNotExist:
                return Response(
                    {"detail": "Job not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not job.pose_data_file:
                return Response(
                    {"detail": "CSV not ready for this job."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            video_url = request.build_absolute_uri(job.input_video.file.url)
            csv_url = request.build_absolute_uri(job.pose_data_file.url)
            norm_csv_url = request.build_absolute_uri(job.norm_pose_data_file.url)
            video_id = job.input_video.id
            return Response({
                "video1": video_url,
                "csv_url": csv_url,
                "norm_csv_url": norm_csv_url,
                "video_id": video_id,
            }, status=status.HTTP_200_OK)

        # Find the latest VideoJob with a completed pose CSV
        latest_job = (
            VideoJob.objects.filter(pose_data_file__isnull=False)
            .order_by("-created_at")
            .first()
        )
        if not latest_job or not latest_job.pose_data_file:
            return Response(
                {"detail": "No processed video and CSV found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        video_url = request.build_absolute_uri(latest_job.input_video.file.url)
        csv_url = request.build_absolute_uri(latest_job.pose_data_file.url)
        norm_csv_url = request.build_absolute_uri(latest_job.norm_pose_data_file.url)
        video_id = latest_job.input_video.id
        return Response({
            "video1": video_url,
            "csv_url": csv_url,
            "norm_csv_url": norm_csv_url,
            "video_id": video_id,
        }, status=status.HTTP_200_OK)


# video deletion endpoint
class VideoDeleteAPIView(APIView):
    """
    API View to delete a video and its associated jobs, or a specific job if job_id is provided.
    If no job_id is given, only the latest job for the video is deleted.
    """

    def delete(self, request, video_id, *args, **kwargs):
        job_id = request.query_params.get("job_id")
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            logger.warning(f"Delete request for non-existent video_id: {video_id}")
            return Response(
                {"detail": "Video not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if job_id:
            # Delete only the specific job and its CSV
            try:
                video_job = VideoJob.objects.get(id=job_id, input_video=video)
            except VideoJob.DoesNotExist:
                return Response(
                    {"detail": "Job not found for this video."}, status=status.HTTP_404_NOT_FOUND
                )
            delete_csv(video_job.pose_data_file)
            delete_norm_csv(video_job.norm_pose_data_file)
            video_job.delete()
            logger.info(f"Deleted job {job_id} and its CSV for video {video.id}")
            # If no more jobs exist for this video, delete the video file
            if not VideoJob.objects.filter(input_video=video).exists():
                video.delete()
                logger.info(f"Video {video.id} deleted as it had no more jobs")
            return Response(
                {"detail": "Job and associated CSV deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        else:
            # Delete only the latest job for this video
            latest_job = (
                VideoJob.objects.filter(input_video=video)
                .order_by("-created_at")
                .first()
            )
            if not latest_job:
                return Response(
                    {"detail": "No jobs found for this video."}, status=status.HTTP_404_NOT_FOUND
                )
            delete_csv(latest_job.pose_data_file)
            delete_norm_csv(latest_job.norm_pose_data_file)
            latest_job.delete()
            logger.info(f"Deleted latest job and its CSV for video {video.id}")
            # If no more jobs exist for this video, delete the video file
            if not VideoJob.objects.filter(input_video=video).exists():
                video.delete()
                logger.info(f"Video {video.id} deleted as it had no more jobs")
            return Response(
                {"detail": "Latest job and associated CSV deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )

# for regenerate the csv
class VideoRegenerateCSVAPIView(APIView):
    """
    API View to regenerate the pose CSV for a specific job, or for the latest job if no job_id is given.
    """

    def post(self, request, video_id, *args, **kwargs):
        job_id = request.query_params.get("job_id")
        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            logger.warning(f"Regenerate CSV request for non-existent video_id: {video_id}")
            return Response({"detail": "Video not found."}, status=status.HTTP_404_NOT_FOUND)

        if job_id:
            # Regenerate for a specific job
            try:
                video_job = VideoJob.objects.get(id=job_id, input_video=video)
            except VideoJob.DoesNotExist:
                return Response(
                    {"detail": "Job not found for this video."}, status=status.HTTP_404_NOT_FOUND
                )
            delete_csv(video_job.pose_data_file)
            delete_norm_csv(video_job.norm_pose_data_file)
            video_to_pose_data_task.delay(str(video_job.id))
            logger.info(
                f"Celery task video_to_pose_data_task dispatched for job {video_job.id}"
            )
        else:
            # Regenerate for the latest job of this video
            latest_job = (
                VideoJob.objects.filter(input_video=video)
                .order_by("-created_at")
                .first()
            )
            if not latest_job:
                return Response(
                    {"detail": "No jobs found for this video."}, status=status.HTTP_404_NOT_FOUND
                )
            delete_csv(latest_job.pose_data_file)
            delete_norm_csv(latest_job.norm_pose_data_file)
            video_to_pose_data_task.delay(str(latest_job.id))
            logger.info(
                f"Celery task video_to_pose_data_task dispatched for latest job {latest_job.id} of video {video.id}"
            )
        return Response({"detail": "CSV regeneration initiated."}, status=status.HTTP_202_ACCEPTED)

class VideoListAPIView(APIView):
    """
    API View to list all videos.
    """

    def get(self, request, *args, **kwargs):
        videos = Video.objects.all()
        serializer = VideoSerializer(videos, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class JobListAPIView(APIView):
    """
    API View to list all jobs and their status.
    """
    def get(self, request, *args, **kwargs):
        jobs = VideoJob.objects.select_related("input_video").all().order_by("-created_at")
        data = []
        for job in jobs:
            data.append({
                "id": str(job.id),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "pose_data_file": request.build_absolute_uri(job.pose_data_file.url) if job.pose_data_file else None,
                "input_video": {
                    "id": str(job.input_video.id),
                    "file": request.build_absolute_uri(job.input_video.file.url) if job.input_video and job.input_video.file else "",
                },
            })
        return Response(data, status=status.HTTP_200_OK)
