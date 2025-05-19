# apps/video_processing/models.py

import hashlib
import uuid
import os
from django.db import models
from django.conf import settings


def get_hashed_video_upload_path(instance, filename):
    ext = filename.split(".")[-1]
    if not ext:
        ext = "bin"  # Default extension if none found
    unique_filename = f"{uuid.uuid4()}.{ext.lower()}"
    return os.path.join("videos_hashed", unique_filename)


class Video(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the video record.",
    )
    file = models.FileField(
        upload_to=get_hashed_video_upload_path,
        help_text="The video file. Stored with a unique name (UUID based).",
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        help_text="Original name of the uploaded file by the user.",
    )
    file_hash = models.CharField(
        max_length=64,  # SHA256 hex digest
        unique=True,  # Ensures content deduplication
        blank=True,  # Will be calculated on save
        null=True,  # Allows null if hashing fails or file not present initially
        db_index=True,
        help_text="SHA256 hash of the video file content for deduplication.",
    )
    filesize = models.PositiveIntegerField(
        null=True, blank=True, help_text="Size of the video file in bytes."
    )
    content_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="MIME type of the video file (e.g., video/mp4).",
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the video record was created."
    )

    def _calculate_file_hash(self):
        """Calculates SHA256 hash of the file content."""
        if not self.file:
            return None
        sha256_hash = hashlib.sha256()
        try:
            self.file.seek(0)
            for chunk in iter(lambda: self.file.read(4096), b""):
                sha256_hash.update(chunk)
            self.file.seek(0)
            return sha256_hash.hexdigest()
        except Exception:
            # Log error appropriately in a real application
            return None

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "name") and not self.original_filename:
            self.original_filename = os.path.basename(self.file.name)

        if self.file and not self.file_hash:  # Calculate hash only if not already set
            self.file_hash = self._calculate_file_hash()

        if self.file and hasattr(self.file, "size") and self.filesize is None:
            try:
                self.filesize = self.file.size
            except Exception:
                pass  # Handle error

        # Basic content type detection from extension
        if self.file and hasattr(self.file, "name") and not self.content_type:
            name, ext = os.path.splitext(self.original_filename or self.file.name)
            ext = ext.lower()
            content_types = {
                ".mp4": "video/mp4",
                ".mov": "video/quicktime",
                ".avi": "video/x-msvideo",
                ".wmv": "video/x-ms-wmv",
                ".webm": "video/webm",
                ".mkv": "video/x-matroska",
            }
            self.content_type = content_types.get(ext)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_filename or str(self.id)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Video File"
        verbose_name_plural = "Video Files"


def get_pose_data_upload_path(instance, filename):
    """
    Generates a unique upload path for intermediate pose data CSVs.
    Filename will be <job_id>_posedata_v<version>.csv.
    """
    job_id = instance.id if instance.id else uuid.uuid4()
    # The 'filename' argument might be the original, but we enforce our own.
    new_filename = f"{job_id}_posedata.csv"
    return os.path.join("intermediate_data", "pose_csvs", new_filename)


class VideoJob(models.Model):
    """
    Represents and tracks a video processing job through its various stages.
    """

    class JobStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Upload"
        UPLOADED = "UPLOADED", "Uploaded, Awaiting Pose Extraction"
        POSE_EXTRACTION_QUEUED = "POSE_EXTRACTION_QUEUED", "Pose Extraction Queued"
        EXTRACTING_POSE = "EXTRACTING_POSE", "Extracting Pose Data"
        POSE_DATA_GENERATED = (
            "POSE_DATA_GENERATED",
            "Pose Data Generated, Awaiting Armature Video",
        )
        ARMATURE_VIDEO_QUEUED = "ARMATURE_VIDEO_QUEUED", "Armature Video Queued"
        GENERATING_ARMATURE_VIDEO = (
            "GENERATING_ARMATURE_VIDEO",
            "Generating Armature Video",
        )
        COMPLETED = "COMPLETED", "Processing Completed"
        FAILED = "FAILED", "Processing Failed"
        CLEANED_UP = "CLEANED_UP", "Output Cleaned Up"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the job.",
    )
    status = models.CharField(
        max_length=30,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        help_text="Current status of the processing job.",
    )
    # Link to the uploaded Video instance
    input_video = models.ForeignKey(
        Video,
        on_delete=models.PROTECT,
        null=True,  # Becomes non-null after successful upload and Video object creation
        related_name="jobs_as_input",
        help_text="The input video file for this job.",
    )

    pose_algorithm_id = models.PositiveIntegerField(
        help_text="Version of the pose extraction process used for this job.",
    )
    # Path to the intermediate pose data CSV file.
    # Using FileField for easier management with Django's storage system.
    pose_data_file = models.FileField(
        upload_to=get_pose_data_upload_path,
        null=True,
        blank=True,
        help_text="Intermediate pose data CSV file generated by the first job stage.",
    )
    # Path or reference to the final output video.
    # Could be a FileField if you create another Video model instance for output,
    # or a CharField if it's a temporary path managed differently.
    output_video_path = models.CharField(
        max_length=1024,
        null=True,
        blank=True,
        help_text="Path or identifier for the final processed output video file.",
    )
    output_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the final output video was generated.",
    )
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the job was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the job was last updated."
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message captured if the processing job fails or encounters an issue."
    )
    celery_pose_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Celery Task ID for pose extraction.",
    )
    celery_armature_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Celery Task ID for armature video generation.",
    )

    def __str__(self):
        return f"Job {self.id} ({self.get_status_display()})"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Video Job"
        verbose_name_plural = "Video Jobs"
