from rest_framework import serializers
from .models import Video, VideoJob

class VideoSerializer(serializers.ModelSerializer):
    """
    Serializer for the Video model.
    Handles creation of Video instances from uploaded files.
    The model's save() method handles hash calculation and file renaming.
    """
    class Meta:
        model = Video
        fields = [
            'id',
            'file', # This will be used for file uploads
            'original_filename',
            'file_hash',
            'filesize',
            'content_type',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'original_filename', # Populated by model's save method
            'file_hash',         # Populated by model's save method
            'filesize',          # Populated by model's save method
            'content_type',      # Populated by model's save method
            'uploaded_at',
        ]

    def create(self, validated_data):
        """
        The 'file' from validated_data is an UploadedFile instance.
        The Video model's save() method will handle the hashing and
        saving the file to the correct path.
        """
        video = Video.objects.create(**validated_data)
        return video

class VideoJobCreateSerializer(serializers.Serializer):
    video_file = serializers.FileField(write_only=True, help_text="The video file to be processed.")
    pose_algorithm_id = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="ID of the pose estimation algorithm to use (e.g., 1 for Lite, 2 for Full, 3 for Heavy MediaPipe model)."
    )

class VideoJobDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for the VideoJob model, used for displaying job details and status.
    """
    input_video_details = VideoSerializer(source='input_video', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True) # Human-readable status

    class Meta:
        model = VideoJob
        fields = [
            'id',
            'status',
            'status_display', # Human-readable status
            'input_video', # ID of the input video
            'input_video_details', # Nested details of the input video
            'pose_algorithm_id',
            'pose_data_file', # URL to the generated CSV
            'output_video_path', # Path or URL to the final video
            'output_generated_at',
            'error_message',
            'created_at',
            'updated_at',
            'celery_pose_task_id',
            'celery_armature_task_id',
        ]
        read_only_fields = [
            'id',
            'status',
            'status_display',
            'input_video_details',
            'pose_data_file',
            'output_video_path',
            'output_generated_at',
            'error_message',
            'created_at',
            'updated_at',
            'celery_pose_task_id',
            'celery_armature_task_id',
        ]

    # If you want pose_data_file to return a full URL:
    def get_pose_data_file_url(self, obj):
        request = self.context.get('request')
        if obj.pose_data_file and hasattr(obj.pose_data_file, 'url'):
            if request:
                return request.build_absolute_uri(obj.pose_data_file.url)
            return obj.pose_data_file.url
        return None

    # You might need to adjust field representation, e.g., for FileField to return URL
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')

        # Ensure FileField returns full URL if a request context is available
        if instance.pose_data_file and hasattr(instance.pose_data_file, 'url'):
            if request:
                representation['pose_data_file'] = request.build_absolute_uri(instance.pose_data_file.url)
            else:
                representation['pose_data_file'] = instance.pose_data_file.url
        else:
            representation['pose_data_file'] = None # Or an empty string

        return representation

